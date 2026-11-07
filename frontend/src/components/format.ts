// Ported from macros.html's kg()/naira() - same formatting, as plain
// TypeScript functions instead of Jinja2 macros.
export function formatKg(value: number | null | undefined, decimals = 0): string {
  return (value ?? 0).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function formatNaira(value: number | null | undefined): string {
  return '₦' + (value ?? 0).toLocaleString('en-US', { maximumFractionDigits: 0 })
}
