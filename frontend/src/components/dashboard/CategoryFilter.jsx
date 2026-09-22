import React from 'react';
import { CATEGORIES } from '../../lib/constants.js';

/**
 * Swiss Category Filter Strip for Indian Edition Feeds.
 * Conforms to Ponytail Ultra: zero state machines, pure functional event dispatching.
 *
 * @param {object} props
 * @param {string} [props.activeCategory='ALL'] - Currently selected active category
 * @param {(category: string) => void} props.onSelectCategory - Category switch callback
 * @param {readonly string[]} [props.categories=CATEGORIES] - Category list to display
 * @param {string} [props.className=''] - Additional styling classes
 */
export function CategoryFilter({
  activeCategory = 'ALL',
  onSelectCategory,
  categories = CATEGORIES,
  className = '',
}) {
  return (
    <nav
      aria-label="Categories"
      className={`w-full overflow-x-auto border-b-2 border-swiss-black bg-swiss-white py-2 flex items-center gap-2 select-none ${className}`}
    >
      {categories.map((category, index) => {
        const isActive = activeCategory === category;
        const prefix = String(index + 1).padStart(2, '0');

        return (
          <button
            key={category}
            type="button"
            onClick={() => onSelectCategory && onSelectCategory(category)}
            className={`px-4 py-2 text-xs font-bold uppercase tracking-wider rounded-none border-2 border-swiss-black transition-colors duration-100 cursor-pointer focus:outline-none focus:ring-2 focus:ring-swiss-black ${
              isActive
                ? 'bg-swiss-black text-swiss-white'
                : 'bg-swiss-white text-swiss-black hover:bg-neutral-100'
            }`}
          >
            <span className="opacity-60 mr-1.5 font-mono">{prefix} //</span>
            {category}
          </button>
        );
      })}
    </nav>
  );
}
