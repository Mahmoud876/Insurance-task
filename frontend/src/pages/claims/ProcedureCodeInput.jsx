import { useEffect, useRef, useState } from 'react';

export default function ProcedureCodeInput({ value, onChange, onKeyDown, inputRef }) {
  const [options, setOptions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const ideaRef = useRef(null);
  const timeoutRef = useRef(null);

  useEffect(() => {
    const query = (value ?? '').trim();

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    if (!query) {
      setOptions([]);
      setIsOpen(false);
      return undefined;
    }

    timeoutRef.current = window.setTimeout(async () => {
      try {
        const response = await fetch(`/v1/reference/procedure-codes?query=${encodeURIComponent(query)}`);

        if (!response.ok) {
          return;
        }

        const data = await response.json();
        setOptions(Array.isArray(data) ? data : []);
        setHighlightedIndex(0);
        setIsOpen(Array.isArray(data) && data.length > 0);
      } catch {
        setOptions([]);
        setIsOpen(false);
      }
    }, 150);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [value]);

  function handleSelect(option) {
    if (!option) {
      return;
    }

    onChange(option.code);
    setOptions([]);
    setIsOpen(false);
    setHighlightedIndex(0);

    window.setTimeout(() => {
      ideaRef.current?.focus();
      ideaRef.current?.select?.();
    }, 0);
  }

  function handleKeyDown(event) {
    if (isOpen && options.length > 0) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setHighlightedIndex((index) => (index + 1) % options.length);
        return;
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setHighlightedIndex((index) => (index - 1 + options.length) % options.length);
        return;
      }

      if (event.key === 'Enter' || (event.key === 'Tab' && !event.shiftKey)) {
        event.preventDefault();
        handleSelect(options[highlightedIndex] ?? options[0]);
        return;
      }
    }

    onKeyDown?.(event);
  }

  return (
    <div className="relative">
      <input
        ref={(node) => {
          inputRef?.(node);
          ideaRef.current = node;
        }}
        type="text"
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value.toUpperCase())}
        onFocus={() => {
          if (options.length > 0) {
            setIsOpen(true);
          }
        }}
        onBlur={() => {
          window.setTimeout(() => setIsOpen(false), 120);
        }}
        onKeyDown={handleKeyDown}
        className="w-full rounded-md border border-slate-300 px-2 py-2 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
        placeholder="Procedure"
      />

      {isOpen && options.length > 0 ? (
        <ul
          role="listbox"
          className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-md border border-slate-200 bg-white shadow-lg"
        >
          {options.map((option, index) => (
            <li key={option.code}>
              <button
                type="button"
                role="option"
                aria-selected={index === highlightedIndex}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => handleSelect(option)}
                className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm ${
                  index === highlightedIndex ? 'bg-slate-100' : 'bg-white hover:bg-slate-50'
                }`}
              >
                <span className="font-medium text-slate-900">{option.code}</span>
                <span className="text-xs text-slate-500">{option.category}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
