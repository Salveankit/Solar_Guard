export const formatInteger = (value: number): string =>
  new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);

export const formatKwh = (value: number): string =>
  `${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(value)} kWh`;

export const formatInr = (value: number): string =>
  `₹${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value)}`;

export const formatKm = (value: number): string =>
  `${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(value)} km`;

export const formatMinutes = (value: number): string =>
  `${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value)} min`;

export const formatPercent = (value: number): string =>
  `${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value)}%`;
