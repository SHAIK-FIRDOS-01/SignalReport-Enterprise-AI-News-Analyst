import React from 'react';

/**
 * Stark Swiss Metadata Badge / Edition Chip.
 * Conforms to Ponytail Ultra: zero state, pure functional presentation.
 *
 * @param {object} props
 * @param {React.ReactNode} props.children - Badge content / label text
 * @param {'default' | 'inverted' | 'red'} [props.variant='default'] - Visual theme preset
 * @param {boolean} [props.live=false] - When true, renders a pulsating status dot
 * @param {string} [props.className=''] - Additional styling classes
 */
export function SwissBadge({
  children,
  variant = 'default',
  live = false,
  className = '',
  ...props
}) {
  const baseStyles =
    'inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-bold uppercase tracking-wider rounded-none select-none';

  const variantStyles = {
    default: 'border border-swiss-black bg-swiss-white text-swiss-black',
    inverted: 'border border-swiss-black bg-swiss-black text-swiss-white',
    red: 'border border-swiss-black bg-swiss-red text-swiss-white',
  };

  const activeVariant = variantStyles[variant] || variantStyles.default;

  return (
    <span className={`${baseStyles} ${activeVariant} ${className}`} {...props}>
      {live && (
        <span
          data-testid="swiss-badge-live-indicator"
          className="w-2 h-2 rounded-none bg-swiss-red animate-pulse inline-block"
        />
      )}
      {children}
    </span>
  );
}
