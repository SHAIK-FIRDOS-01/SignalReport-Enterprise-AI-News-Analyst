import React from 'react';

/**
 * Stark Swiss Action Button.
 * Conforms to Ponytail Ultra: zero complex wrappers or state machines.
 *
 * @param {object} props
 * @param {React.ReactNode} props.children
 * @param {'primary' | 'secondary' | 'destructive'} [props.variant='primary']
 * @param {'button' | 'submit' | 'reset'} [props.type='button']
 * @param {boolean} [props.disabled=false]
 * @param {function} [props.onClick]
 * @param {string} [props.className='']
 */
export function SwissButton({
  children,
  variant = 'primary',
  type = 'button',
  disabled = false,
  onClick,
  className = '',
  ...props
}) {
  const baseStyles =
    'inline-flex items-center justify-center px-6 py-2 text-sm font-bold uppercase tracking-wider rounded-none border-2 transition-colors duration-100 focus:outline-none focus:ring-2 focus:ring-swiss-black focus:ring-offset-2 select-none';

  const variantStyles = {
    primary:
      'bg-swiss-black text-swiss-white border-swiss-black hover:bg-swiss-white hover:text-swiss-black',
    secondary:
      'bg-swiss-white text-swiss-black border-swiss-black hover:bg-swiss-black hover:text-swiss-white',
    destructive:
      'bg-swiss-red text-swiss-white border-swiss-black hover:bg-swiss-black',
  };

  const activeVariant = variantStyles[variant] || variantStyles.primary;
  const stateStyles = disabled
    ? 'opacity-50 cursor-not-allowed pointer-events-none'
    : 'cursor-pointer active:translate-y-[1px]';

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={disabled ? undefined : onClick}
      className={`${baseStyles} ${activeVariant} ${stateStyles} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
