import React from 'react';

/**
 * Monospaced/High-Contrast Swiss Text Input with Dedicated Sanitized Error Slot.
 * Conforms to Ponytail Ultra: zero external dependencies, native React hooks & standard DOM.
 *
 * @param {object} props
 * @param {string} props.id - Input element ID for label pairing
 * @param {string} [props.label] - Uppercase descriptor label
 * @param {string} [props.type='text'] - HTML input type (text, email, password, etc.)
 * @param {string} [props.placeholder=''] - Monospaced placeholder text
 * @param {string} [props.value] - Controlled input value
 * @param {function} [props.onChange] - Native change event handler
 * @param {string} [props.error] - Validation error message
 * @param {boolean} [props.disabled=false] - Interactive disabled flag
 * @param {string} [props.className=''] - Custom container classes
 */
export function SwissInput({
  id,
  label,
  type = 'text',
  placeholder = '',
  value,
  onChange,
  error,
  disabled = false,
  className = '',
  ...props
}) {
  const baseInputStyles =
    'w-full px-3 py-2 text-sm text-swiss-black bg-swiss-white rounded-none border-2 border-swiss-black placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-swiss-black focus:ring-offset-2 transition-colors duration-100';
  const stateStyles = disabled
    ? 'opacity-50 cursor-not-allowed bg-neutral-100'
    : 'cursor-text';

  return (
    <div className={`flex flex-col ${className}`}>
      {label && (
        <label
          htmlFor={id}
          className="text-xs font-bold uppercase tracking-wider text-swiss-black mb-1 select-none"
        >
          {label}
        </label>
      )}
      <input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        disabled={disabled}
        className={`${baseInputStyles} ${stateStyles}`}
        {...props}
      />
      <div
        data-testid="swiss-input-error"
        className="min-h-[1.25rem] mt-1 text-xs font-bold uppercase tracking-wider text-swiss-red select-none"
      >
        {error ? String(error) : ''}
      </div>
    </div>
  );
}
