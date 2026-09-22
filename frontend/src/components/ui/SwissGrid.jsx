import React from 'react';

/**
 * SwissGrid container component enforcing a stark 2px black bounding box.
 * Conforms to Ponytail Ultra: pure CSS grid wrapper with zero dynamic JS layout calculations.
 *
 * @param {object} props
 * @param {React.ReactNode} props.children
 * @param {string} [props.className='']
 * @param {number} [props.cols=12]
 */
export function SwissGrid({ children, className = '', cols = 12, ...props }) {
  const colClass = cols === 12 ? 'grid-cols-1 lg:grid-cols-12' : `grid-cols-${cols}`;

  return (
    <div
      className={`grid w-full border-2 border-swiss-black ${colClass} ${className}`}
      data-testid="swiss-grid"
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * SwissGridCell sub-component rendering an uppercase section marker ('01 //') and structural borders.
 *
 * @param {object} props
 * @param {React.ReactNode} props.children
 * @param {string} [props.tag] - Uppercase section index or label (e.g., '01 //')
 * @param {number} [props.span=6] - Column span count (1–12)
 * @param {boolean} [props.borderRight=false] - Apply 2px right border
 * @param {boolean} [props.borderBottom=false] - Apply 2px bottom border
 * @param {string} [props.className='']
 */
export function SwissGridCell({
  children,
  tag,
  span = 6,
  borderRight = false,
  borderBottom = false,
  className = '',
  ...props
}) {
  const spanClass = span ? `lg:col-span-${span}` : '';
  const rBorder = borderRight ? 'lg:border-r-2 border-swiss-black' : '';
  const bBorder = borderBottom ? 'border-b-2 border-swiss-black' : '';

  return (
    <div
      className={`flex flex-col p-4 ${spanClass} ${rBorder} ${bBorder} ${className}`}
      data-testid="swiss-grid-cell"
      {...props}
    >
      {tag && (
        <span
          className="font-mono text-xs uppercase tracking-widest text-swiss-black mb-2 select-none"
          data-testid="swiss-grid-cell-tag"
        >
          {tag}
        </span>
      )}
      {children}
    </div>
  );
}
