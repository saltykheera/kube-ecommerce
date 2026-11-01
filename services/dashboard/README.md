# React + Vite

## Demo login credentials

The login defaults, password hint, and Admin/Member quick-fill buttons share the
same account configuration. Local builds use the local demo passwords. Cloud demo
builds set `VITE_DEMO_ADMIN_PASSWORD` and `VITE_DEMO_MEMBER_PASSWORD` to match the
deployed accounts. The Dockerfile accepts both as build arguments.

These values are intentionally visible on the login page and included in the
public JavaScript bundle. Use them only for public demo accounts, never private
production credentials. Changing a build value does not change the backend password.

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
