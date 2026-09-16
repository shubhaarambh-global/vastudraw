export type DisplayLengthUnit = "ft-in" | "m";

export const DEFAULT_DISPLAY_LENGTH_UNIT: DisplayLengthUnit = "ft-in";

const MM_PER_INCH = 25.4;
const EIGHTHS_PER_INCH = 8;
const EIGHTHS_PER_FOOT = 12 * EIGHTHS_PER_INCH;

function roundHalfAwayFromZero(value: number): number {
  if (!Number.isFinite(value)) {
    throw new RangeError("Length must be finite.");
  }
  return value < 0 ? -Math.round(-value) : Math.round(value);
}

function gcd(a: number, b: number): number {
  let x = Math.abs(a);
  let y = Math.abs(b);
  while (y !== 0) {
    const next = x % y;
    x = y;
    y = next;
  }
  return x || 1;
}

function fractionText(eighths: number): string {
  if (eighths === 0) return "";
  const divisor = gcd(eighths, EIGHTHS_PER_INCH);
  return `${String(eighths / divisor)}/${String(EIGHTHS_PER_INCH / divisor)}`;
}

export function formatLengthMm(
  valueMm: number,
  unit: DisplayLengthUnit,
): string {
  if (!Number.isSafeInteger(valueMm)) {
    throw new RangeError(
      "Canonical length must be a safe integer millimetre value.",
    );
  }

  if (unit === "m") {
    return `${(valueMm / 1000).toFixed(3)} m`;
  }

  const sign = valueMm < 0 ? "-" : "";
  const totalEighths = roundHalfAwayFromZero(
    (Math.abs(valueMm) / MM_PER_INCH) * EIGHTHS_PER_INCH,
  );
  const feet = Math.floor(totalEighths / EIGHTHS_PER_FOOT);
  const remaining = totalEighths % EIGHTHS_PER_FOOT;
  const inches = Math.floor(remaining / EIGHTHS_PER_INCH);
  const eighths = remaining % EIGHTHS_PER_INCH;
  const fraction = fractionText(eighths);
  const inchText = fraction ? `${String(inches)} ${fraction}` : String(inches);
  return `${sign}${String(feet)}'-${inchText}"`;
}

function parseNumber(text: string): number {
  const value = Number(text);
  if (!Number.isFinite(value)) {
    throw new RangeError("Length must be a finite number.");
  }
  return value;
}

function parseMixedNumber(text: string): number {
  const normalized = text.trim();
  const mixed = /^(\d+(?:\.\d+)?)\s+(\d+)\/(\d+)$/.exec(normalized);
  if (mixed) {
    const whole = parseNumber(mixed[1] ?? "");
    const numerator = parseNumber(mixed[2] ?? "");
    const denominator = parseNumber(mixed[3] ?? "");
    if (denominator === 0) {
      throw new RangeError("Fraction denominator must not be zero.");
    }
    return whole + numerator / denominator;
  }

  const fraction = /^(\d+)\/(\d+)$/.exec(normalized);
  if (fraction) {
    const numerator = parseNumber(fraction[1] ?? "");
    const denominator = parseNumber(fraction[2] ?? "");
    if (denominator === 0) {
      throw new RangeError("Fraction denominator must not be zero.");
    }
    return numerator / denominator;
  }

  return parseNumber(normalized);
}

function mmFromMetres(value: number): number {
  return roundHalfAwayFromZero(value * 1000);
}

function mmFromInches(value: number): number {
  return roundHalfAwayFromZero(value * MM_PER_INCH);
}

function normalizeUnitText(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replaceAll("’", "'")
    .replaceAll("′", "'")
    .replaceAll("“", '"')
    .replaceAll("”", '"')
    .replaceAll("″", '"');
}

export function parseLengthToMm(
  input: string,
  defaultUnit: DisplayLengthUnit,
): number {
  const text = normalizeUnitText(input);
  if (!text) {
    throw new RangeError("Length is required.");
  }

  const mmMatch = /^([+-]?\d+(?:\.\d+)?)\s*mm$/.exec(text);
  if (mmMatch) {
    return roundHalfAwayFromZero(parseNumber(mmMatch[1] ?? ""));
  }

  const metreMatch =
    /^([+-]?\d+(?:\.\d+)?)\s*(?:m|metre|metres|meter|meters)$/.exec(text);
  if (metreMatch) {
    return mmFromMetres(parseNumber(metreMatch[1] ?? ""));
  }

  const inchOnly =
    /^([+-]?)(\d+(?:\.\d+)?(?:\s+\d+\/\d+)?|\d+\/\d+)\s*(?:"|in|inch|inches)$/.exec(
      text,
    );
  if (inchOnly) {
    const sign = inchOnly[1] === "-" ? -1 : 1;
    return sign * mmFromInches(parseMixedNumber(inchOnly[2] ?? ""));
  }

  const feetMatch =
    /^([+-]?)(\d+(?:\.\d+)?)\s*(?:'|ft|foot|feet)(?:\s*-?\s*(\d+(?:\.\d+)?(?:\s+\d+\/\d+)?|\d+\/\d+)\s*(?:"|in|inch|inches)?)?$/.exec(
      text,
    );
  if (feetMatch) {
    const sign = feetMatch[1] === "-" ? -1 : 1;
    const feet = parseNumber(feetMatch[2] ?? "");
    const inches = feetMatch[3] ? parseMixedNumber(feetMatch[3]) : 0;
    if (inches >= 12) {
      throw new RangeError(
        "Inches must be less than 12 when feet are supplied.",
      );
    }
    return sign * mmFromInches(feet * 12 + inches);
  }

  const bareNumber = /^([+-]?\d+(?:\.\d+)?)$/.exec(text);
  if (bareNumber) {
    const value = parseNumber(bareNumber[1] ?? "");
    return defaultUnit === "m" ? mmFromMetres(value) : mmFromInches(value * 12);
  }

  throw new RangeError(
    "Use feet/inches such as 10'-6 1/2\" or metres such as 3.200 m.",
  );
}
