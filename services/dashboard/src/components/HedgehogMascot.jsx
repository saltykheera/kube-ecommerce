import React from 'react';

/**
 * Hand-drawn PostHog-inspired Hedgehog mascot in various moods/poses.
 * Flat color cartoon illustration, native SVG.
 */
export default function HedgehogMascot({ pose = 'default', size = 32, style = {} }) {
  if (pose === 'terminal') {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ display: 'inline-block', flexShrink: 0, ...style }}
      >
        {/* Hedgehog Spikes */}
        <path
          d="M8 26C6 22 7 16 12 12C16 9 24 8 30 11C36 13 40 18 41 24C42 30 38 35 34 37L10 37C8 34 7 30 8 26Z"
          fill="#33342D"
          stroke="#23251D"
          strokeWidth="2"
        />
        <path d="M11 15L6 11M16 11L14 5M25 9L27 3M33 11L38 6M38 17L44 14" stroke="#23251D" strokeWidth="2" strokeLinecap="round" />
        {/* Face */}
        <circle cx="31" cy="24" r="11" fill="#F4D3A1" stroke="#23251D" strokeWidth="2" />
        {/* Snout */}
        <ellipse cx="40" cy="25" rx="3.5" ry="2.5" fill="#23251D" />
        {/* Eye with glasses/terminal reflection */}
        <circle cx="32" cy="22" r="4" fill="#FFFFFF" stroke="#23251D" strokeWidth="1.5" />
        <circle cx="33" cy="22" r="1.5" fill="#23251D" />
        {/* Cheek */}
        <circle cx="28" cy="27" r="2" fill="#F7A501" opacity="0.6" />
        {/* Mini Terminal / Screen */}
        <rect x="2" y="27" width="18" height="13" rx="2" fill="#23251D" stroke="#4D4F46" strokeWidth="1.5" />
        <rect x="4" y="29" width="14" height="9" fill="#1D4ED8" rx="1" />
        <path d="M6 33L8 35L6 37M10 37H14" stroke="#60A5FA" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    );
  }

  if (pose === 'lab') {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ display: 'inline-block', flexShrink: 0, ...style }}
      >
        {/* Hedgehog Spikes */}
        <path
          d="M8 26C6 22 7 16 12 12C16 9 24 8 30 11C36 13 40 18 41 24C42 30 38 35 34 37L10 37C8 34 7 30 8 26Z"
          fill="#33342D"
          stroke="#23251D"
          strokeWidth="2"
        />
        <path d="M11 15L6 11M16 11L14 5M25 9L27 3M33 11L38 6M38 17L44 14" stroke="#23251D" strokeWidth="2" strokeLinecap="round" />
        {/* Lab Coat Body */}
        <path d="M14 30C14 26 18 24 24 24C30 24 34 26 34 30L34 40L14 40Z" fill="#FFFFFF" stroke="#23251D" strokeWidth="1.5" />
        <path d="M24 24V40" stroke="#BFC1B7" strokeWidth="1.5" />
        {/* Face */}
        <circle cx="31" cy="20" r="9" fill="#F4D3A1" stroke="#23251D" strokeWidth="2" />
        <ellipse cx="38" cy="21" rx="3" ry="2" fill="#23251D" />
        {/* Eye */}
        <circle cx="32" cy="18" r="1.5" fill="#23251D" />
        {/* Glasses */}
        <circle cx="32" cy="18" r="4.5" stroke="#F7A501" strokeWidth="1.5" fill="none" />
        {/* Paws holding test flask */}
        <circle cx="21" cy="32" r="2.5" fill="#F4D3A1" stroke="#23251D" strokeWidth="1" />
        <path d="M18 36L14 42H24L20 36V32H18V36Z" fill="#DCEAF6" stroke="#2C84E0" strokeWidth="1.5" />
      </svg>
    );
  }

  // Default friendly mascot
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ display: 'inline-block', flexShrink: 0, ...style }}
    >
      {/* Spikes */}
      <path
        d="M6 26C4 20 6 13 12 9C17 6 25 5 32 8C39 11 44 17 44 24C44 32 39 38 33 40L10 40C7 36 5 31 6 26Z"
        fill="#33342D"
        stroke="#23251D"
        strokeWidth="2"
      />
      {/* Spikes detail lines */}
      <path d="M10 12L4 7M17 7L15 2M26 6L28 1M34 8L40 4M41 15L47 12M42 22L48 22" stroke="#23251D" strokeWidth="2" strokeLinecap="round" />
      {/* Face */}
      <circle cx="31" cy="24" r="11" fill="#F4D3A1" stroke="#23251D" strokeWidth="2" />
      {/* Nose */}
      <ellipse cx="41" cy="24" rx="3" ry="2" fill="#23251D" />
      {/* Eye with glint */}
      <circle cx="33" cy="20" r="2" fill="#23251D" />
      <circle cx="33.5" cy="19.5" r="0.6" fill="#FFFFFF" />
      {/* Smile */}
      <path d="M34 27C36 28 38 27 39 26" stroke="#23251D" strokeWidth="1.5" strokeLinecap="round" />
      {/* Rosy Cheek */}
      <circle cx="28" cy="26" r="2.5" fill="#F7A501" opacity="0.6" />
      {/* Belly */}
      <ellipse cx="20" cy="30" rx="7" ry="8" fill="#F4D3A1" />
      {/* Little feet */}
      <ellipse cx="14" cy="40" rx="3" ry="1.5" fill="#F4D3A1" stroke="#23251D" strokeWidth="1.5" />
      <ellipse cx="28" cy="40" rx="3" ry="1.5" fill="#F4D3A1" stroke="#23251D" strokeWidth="1.5" />
    </svg>
  );
}
