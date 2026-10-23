#!/usr/bin/env bash
set -euo pipefail

echo "=== [1/6] Ensuring wp-cli & dev auth mu-plugin is installed ==="
WP_POD=$(kubectl get pod -l app.kubernetes.io/name=wordpress -o jsonpath='{.items[0].metadata.name}')

kubectl exec "${WP_POD}" -- bash -c '
if ! command -v wp >/dev/null 2>&1; then
    curl -s -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
    chmod +x wp-cli.phar
    mv wp-cli.phar /usr/local/bin/wp
fi

mkdir -p wp-content/mu-plugins
cat << "EOF" > wp-content/mu-plugins/dev-ssl.php
<?php
/**
 * Plugin Name: Dev REST Auth Helper
 * Description: Enables WooCommerce REST API authentication over local HTTP / Ingress
 */
add_filter("is_ssl", "__return_true", 999);

function dev_extract_basic_auth() {
    if (empty($_SERVER["PHP_AUTH_USER"])) {
        $header = $_SERVER["HTTP_AUTHORIZATION"] ?? $_SERVER["REDIRECT_HTTP_AUTHORIZATION"] ?? "";
        if (stripos($header, "basic ") === 0) {
            $creds = explode(":", base64_decode(substr($header, 6)), 2);
            if (count($creds) === 2) {
                $_SERVER["PHP_AUTH_USER"] = $creds[0];
                $_SERVER["PHP_AUTH_PW"]   = $creds[1];
            }
        }
    }
}
dev_extract_basic_auth();

add_filter("rest_authentication_errors", function($error) {
    if (is_wp_error($error)) {
        return $error;
    }
    dev_extract_basic_auth();
    if (get_current_user_id() === 0 && class_exists("WC_REST_Authentication")) {
        $auth = new WC_REST_Authentication();
        $ref = new ReflectionMethod($auth, "perform_basic_authentication");
        $ref->setAccessible(true);
        $user_id = $ref->invoke($auth);
        if ($user_id) {
            wp_set_current_user((int) $user_id);
            return true;
        }
    }
    return $error;
}, 10);
EOF
'

echo "=== [2/6] Verifying WordPress installation ==="
kubectl exec "${WP_POD}" -- wp core is-installed --allow-root || {
    echo "Installing WordPress core..."
    kubectl exec "${WP_POD}" -- wp core install \
        --url="http://store.local" \
        --title="Kube Ecommerce Store" \
        --admin_user="admin" \
        --admin_password="AdminSecurePassword123!" \
        --admin_email="admin@example.com" \
        --skip-email \
        --allow-root
}

echo "=== [3/6] Setting permalink structure (required for REST API) ==="
kubectl exec "${WP_POD}" -- wp rewrite structure '/%postname%/' --allow-root

echo "=== [4/6] Installing and activating WooCommerce plugin ==="
kubectl exec "${WP_POD}" -- wp plugin is-installed woocommerce --allow-root || {
    echo "Downloading and activating WooCommerce plugin (v9.4.2)..."
    kubectl exec "${WP_POD}" -- wp plugin install woocommerce --version=9.4.2 --activate --allow-root
}
kubectl exec "${WP_POD}" -- wp plugin is-active woocommerce --allow-root || {
    kubectl exec "${WP_POD}" -- wp plugin activate woocommerce --allow-root
}

echo "=== [5/6] Creating default WooCommerce pages & seed data ==="
kubectl exec "${WP_POD}" -- wp wc --allow-root --user=admin tool run install_pages || true

# Seed test product
EXISTING_PROD=$(kubectl exec "${WP_POD}" -- wp post list --post_type=product --field=ID --allow-root | head -n 1 || true)
if [ -z "${EXISTING_PROD}" ]; then
    echo "Creating seed product 'Antigravity Hoodie'..."
    kubectl exec "${WP_POD}" -- wp wc product create \
        --name="Antigravity Hoodie" \
        --type="simple" \
        --regular_price="49.99" \
        --description="Official high performance developer hoodie." \
        --user=admin \
        --allow-root
fi

# Seed test order
EXISTING_ORDER=$(kubectl exec "${WP_POD}" -- wp post list --post_type=shop_order --field=ID --allow-root | head -n 1 || true)
if [ -z "${EXISTING_ORDER}" ]; then
    echo "Creating seed order..."
    kubectl exec "${WP_POD}" -- wp wc shop_order create \
        --status="processing" \
        --customer_id=1 \
        --user=admin \
        --allow-root
fi

echo "=== [6/6] Generating / retrieving WooCommerce REST API keys for MCP Gateway ==="
KEYS_JSON=$(kubectl exec "${WP_POD}" -- wp eval '
global $wpdb;
$user_id = 1;
$description = "MCP Gateway Key";

$existing = $wpdb->get_row($wpdb->prepare(
    "SELECT key_id, consumer_key, consumer_secret FROM {$wpdb->prefix}woocommerce_api_keys WHERE description = %s",
    $description
));

if ($existing) {
    echo json_encode([
        "consumer_key" => $existing->consumer_key,
        "consumer_secret" => $existing->consumer_secret,
        "status" => "existing"
    ]);
} else {
    $consumer_key = "ck_" . wc_rand_hash();
    $consumer_secret = "cs_" . wc_rand_hash();

    $wpdb->insert(
        $wpdb->prefix . "woocommerce_api_keys",
        [
            "user_id" => $user_id,
            "description" => $description,
            "permissions" => "read_write",
            "consumer_key" => wc_api_hash($consumer_key),
            "consumer_secret" => $consumer_secret,
            "truncated_key" => substr($consumer_key, -7),
        ]
    );

    echo json_encode([
        "consumer_key" => $consumer_key,
        "consumer_secret" => $consumer_secret,
        "status" => "created"
    ]);
}
' --allow-root)

echo "WooCommerce Keys Output: ${KEYS_JSON}"

CK=$(echo "${KEYS_JSON}" | jq -r '.consumer_key')
CS=$(echo "${KEYS_JSON}" | jq -r '.consumer_secret')

# If existing was hashed in the database, keep the plaintext from file if already saved
if [ -f woocommerce-keys.env ]; then
    SAVED_CK=$(grep WOOCOMMERCE_CONSUMER_KEY woocommerce-keys.env | cut -d'=' -f2 | tr -d '"')
    SAVED_CS=$(grep WOOCOMMERCE_CONSUMER_SECRET woocommerce-keys.env | cut -d'=' -f2 | tr -d '"')
    if [ -n "${SAVED_CK}" ] && [ -n "${SAVED_CS}" ]; then
        CK="${SAVED_CK}"
        CS="${SAVED_CS}"
    fi
fi

cat <<EOF > woocommerce-keys.env
WOOCOMMERCE_URL="http://store.local"
WOOCOMMERCE_INTERNAL_URL="http://wordpress.default.svc.cluster.local:80"
WOOCOMMERCE_CONSUMER_KEY="${CK}"
WOOCOMMERCE_CONSUMER_SECRET="${CS}"
EOF

echo "WooCommerce setup complete! Credentials saved to woocommerce-keys.env"
