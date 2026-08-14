const CPP_KEYWORDS = new Set(`
alignas alignof and and_eq asm atomic_cancel atomic_commit atomic_noexcept auto
bitand bitor bool break case catch char char8_t char16_t char32_t class compl
concept const consteval constexpr constinit const_cast continue co_await co_return
co_yield decltype default delete do double dynamic_cast else enum explicit export
extern false float for friend goto if inline int long mutable namespace new noexcept
not not_eq nullptr operator or or_eq private protected public reflexpr register
reinterpret_cast requires return short signed sizeof static static_assert static_cast
struct switch synchronized template this thread_local throw true try typedef typeid
typename union unsigned using virtual void volatile wchar_t while xor xor_eq
`.trim().split(/\s+/));

const COMMON_CPP_NAMES = new Set(`
main std vector string wstring u8string array map multimap unordered_map set multiset
unordered_set queue deque stack priority_queue pair tuple optional variant any span
cin cout cerr clog endl flush fixed scientific setprecision ios istream ostream
ifstream ofstream stringstream istringstream ostringstream
sort stable_sort reverse rotate lower_bound upper_bound equal_range binary_search
min max min_element max_element swap gcd lcm iota accumulate inner_product partial_sum
fill fill_n copy copy_if move transform replace remove remove_if unique partition
find find_if count count_if all_of any_of none_of for_each distance next prev begin end
rbegin rend size ssize empty data
push_back emplace_back pop_back push_front emplace_front pop_front push emplace pop top
front back insert erase clear reserve resize capacity shrink_to_fit at first second
make_pair make_tuple tie get make_shared make_unique shared_ptr unique_ptr weak_ptr
numeric_limits function less greater hash move forward declval
abs labs llabs sqrt cbrt pow log log2 log10 exp ceil floor round trunc hypot
memset memcpy memmove strcmp strlen scanf printf puts putchar getchar
sync_with_stdio freopen stdin stdout NULL EOF INT_MAX INT_MIN UINT_MAX LLONG_MAX LLONG_MIN
M_PI size_t ptrdiff_t int8_t int16_t int32_t int64_t uint8_t uint16_t uint32_t uint64_t
exception runtime_error logic_error invalid_argument out_of_range assert
`.trim().split(/\s+/));

const NAME_PARTS = ['sixseven', 'sixtyseven', 'sixone', 'sixtyone'];
const INTEGER_SUFFIX = /(?:[uU](?:ll|LL|l|L)?|(?:ll|LL|l|L)[uU]?)?$/;

function isIdentifierStart(character) {
  return /[A-Za-z_]/.test(character || '');
}

function isIdentifierPart(character) {
  return /[A-Za-z0-9_]/.test(character || '');
}

function consumeQuoted(source, start, quoteIndex) {
  const quote = source[quoteIndex];
  let index = quoteIndex + 1;
  while (index < source.length) {
    if (source[index] === '\\') {
      index += 2;
      continue;
    }
    index += 1;
    if (source[index - 1] === quote) break;
  }
  return source.slice(start, index);
}

function consumeRawString(source, start, rawMarkerIndex) {
  const delimiterStart = rawMarkerIndex + 2;
  const openingParen = source.indexOf('(', delimiterStart);
  if (openingParen === -1 || openingParen - delimiterStart > 16) {
    return consumeQuoted(source, start, rawMarkerIndex + 1);
  }
  const delimiter = source.slice(delimiterStart, openingParen);
  if (/[\s\\()]/.test(delimiter)) {
    return consumeQuoted(source, start, rawMarkerIndex + 1);
  }
  const closing = `)${delimiter}\"`;
  const closingIndex = source.indexOf(closing, openingParen + 1);
  const end = closingIndex === -1 ? source.length : closingIndex + closing.length;
  return source.slice(start, end);
}

function literalAt(source, index) {
  const rest = source.slice(index);
  const raw = rest.match(/^(?:u8|u|U|L)?R\"/);
  if (raw) {
    const marker = index + raw[0].length - 2;
    return consumeRawString(source, index, marker);
  }
  const quoted = rest.match(/^(?:u8|u|U|L)?([\"'])/);
  if (quoted) {
    const quoteIndex = index + quoted[0].length - 1;
    return consumeQuoted(source, index, quoteIndex);
  }
  return null;
}

function consumeNumber(source, start) {
  let index = start;
  let previous = '';
  while (index < source.length) {
    const character = source[index];
    if (/[A-Za-z0-9_'.]/.test(character)) {
      previous = character;
      index += 1;
      continue;
    }
    if ((character === '+' || character === '-') && /[eEpP]/.test(previous)) {
      previous = character;
      index += 1;
      continue;
    }
    break;
  }
  return source.slice(start, index);
}

function consumePreprocessorLine(source, start) {
  let index = start;
  while (index < source.length) {
    const newline = source.indexOf('\n', index);
    if (newline === -1) return source.slice(start);
    let check = newline - 1;
    if (check >= start && source[check] === '\r') check -= 1;
    let backslashes = 0;
    while (check >= start && source[check] === '\\') {
      backslashes += 1;
      check -= 1;
    }
    index = newline + 1;
    if (backslashes % 2 === 0) return source.slice(start, index);
  }
  return source.slice(start);
}

export function tokenizeCpp(source) {
  const tokens = [];
  let index = 0;
  let lineOnlyWhitespace = true;

  const push = (type, text) => {
    tokens.push({type, text});
    if (text.includes('\n')) {
      lineOnlyWhitespace = /^[\t \r]*$/.test(text.slice(text.lastIndexOf('\n') + 1));
    } else if (!/^[\t \r]*$/.test(text)) {
      lineOnlyWhitespace = false;
    }
    index += text.length;
  };

  while (index < source.length) {
    const character = source[index];
    if (lineOnlyWhitespace && character === '#') {
      push('preprocessor', consumePreprocessorLine(source, index));
      continue;
    }
    if (/\s/.test(character)) {
      const match = source.slice(index).match(/^\s+/)[0];
      push('whitespace', match);
      continue;
    }
    if (source.startsWith('//', index)) {
      const newline = source.indexOf('\n', index);
      push('comment', source.slice(index, newline === -1 ? source.length : newline));
      continue;
    }
    if (source.startsWith('/*', index)) {
      const closing = source.indexOf('*/', index + 2);
      push('comment', source.slice(index, closing === -1 ? source.length : closing + 2));
      continue;
    }
    const literal = literalAt(source, index);
    if (literal) {
      push('literal', literal);
      continue;
    }
    if (/[0-9]/.test(character) || (character === '.' && /[0-9]/.test(source[index + 1] || ''))) {
      push('number', consumeNumber(source, index));
      continue;
    }
    if (isIdentifierStart(character)) {
      let end = index + 1;
      while (isIdentifierPart(source[end])) end += 1;
      push('identifier', source.slice(index, end));
      continue;
    }
    push('punctuation', character);
  }
  return tokens;
}

function integerParts(text) {
  if (text.includes('_')) return null;
  const suffixMatch = text.match(INTEGER_SUFFIX);
  const suffix = suffixMatch ? suffixMatch[0] : '';
  const body = text.slice(0, text.length - suffix.length).replaceAll("'", '');
  let radix = 10;
  let digits = body;
  if (/^0[xX][0-9a-fA-F]+$/.test(body)) {
    radix = 16;
    digits = body.slice(2);
  } else if (/^0[bB][01]+$/.test(body)) {
    radix = 2;
    digits = body.slice(2);
  } else if (/^0[0-7]+$/.test(body) && body.length > 1) {
    radix = 8;
    digits = body.slice(1);
  } else if (!/^(?:0|[1-9][0-9]*)$/.test(body)) {
    return null;
  }
  try {
    return {value: BigInt(parseBigIntDigits(digits || '0', radix)), suffix};
  } catch {
    return null;
  }
}

function parseBigIntDigits(digits, radix) {
  let value = 0n;
  const base = BigInt(radix);
  for (const digit of digits.toLowerCase()) {
    const code = digit >= 'a' ? digit.charCodeAt(0) - 87 : Number(digit);
    if (!Number.isInteger(code) || code < 0 || code >= radix) throw new Error('invalid digit');
    value = value * base + BigInt(code);
  }
  return value;
}

function themedAtoms(suffix) {
  const decorate = (value) => `${value}${suffix}`;
  return {
    zero: `(${decorate(67)} ^ ${decorate(67)})`,
    one: `(${decorate(7)} - ${decorate(6)})`,
    two: `((${decorate(7)} - ${decorate(6)}) + (${decorate(7)} - ${decorate(6)}))`,
  };
}

function commonInteger(value, suffix) {
  const number = value.toString();
  const decorate = (item) => `${item}${suffix}`;
  const atoms = themedAtoms(suffix);
  const replacements = {
    '0': atoms.zero,
    '1': atoms.one,
    '2': atoms.two,
    '6': `(${decorate(67)} - ${decorate(61)})`,
    '7': `(${decorate(6)} + ${atoms.one})`,
    '61': `(${decorate(67)} - ${decorate(6)})`,
    '67': `(${decorate(61)} + ${decorate(6)})`,
  };
  return replacements[number] || null;
}

function fullInteger(value, suffix) {
  const atoms = themedAtoms(suffix);
  if (value === 0n) return atoms.zero;
  const bits = value.toString(2);
  let expression = atoms.one;
  for (const bit of bits.slice(1)) {
    expression = `(${expression} * ${atoms.two}${bit === '1' ? ` + ${atoms.one}` : ''})`;
  }
  return expression;
}

function generatedName(sequence) {
  let value = sequence;
  const parts = [];
  do {
    parts.unshift(NAME_PARTS[value % NAME_PARTS.length]);
    value = Math.floor(value / NAME_PARTS.length) - 1;
  } while (value >= 0);
  return parts.join('_');
}

function preprocessorIdentifiers(tokens) {
  const names = new Set();
  for (const token of tokens) {
    if (token.type !== 'preprocessor') continue;
    for (const match of token.text.matchAll(/[A-Za-z_][A-Za-z0-9_]*/g)) names.add(match[0]);
  }
  return names;
}

function parsePreservedNames(value) {
  if (value instanceof Set) return new Set(value);
  if (Array.isArray(value)) return new Set(value);
  return new Set(String(value || '').split(/[\s,]+/).filter(Boolean));
}

export function transformCpp(source, options = {}) {
  const numericMode = ['off', 'common', 'all'].includes(options.numericMode)
    ? options.numericMode
    : 'common';
  const renameIdentifiers = options.renameIdentifiers !== false;
  const tokens = tokenizeCpp(String(source));
  const preserved = new Set([
    ...CPP_KEYWORDS,
    ...COMMON_CPP_NAMES,
    ...preprocessorIdentifiers(tokens),
    ...parsePreservedNames(options.preservedNames),
  ]);
  const sourceNames = new Set(tokens.filter((token) => token.type === 'identifier').map((token) => token.text));
  const unavailableNames = new Set([...preserved, ...sourceNames]);
  const mapping = new Map();
  const warnings = new Set();
  let sequence = 0;
  let integerCount = 0;
  let skippedNumberCount = 0;

  const replacementName = (name) => {
    if (!renameIdentifiers || preserved.has(name) || name.startsWith('_')) return name;
    if (!mapping.has(name)) {
      let candidate;
      do {
        candidate = generatedName(sequence);
        sequence += 1;
      } while (unavailableNames.has(candidate));
      mapping.set(name, candidate);
      unavailableNames.add(candidate);
    }
    return mapping.get(name);
  };

  const output = tokens.map((token) => {
    if (token.type === 'identifier') return replacementName(token.text);
    if (token.type !== 'number' || numericMode === 'off') return token.text;
    const parsed = integerParts(token.text);
    if (!parsed) {
      skippedNumberCount += 1;
      return token.text;
    }
    if (parsed.value.toString(2).length > 256) {
      warnings.add('An integer wider than 256 bits was left unchanged to prevent a small output apocalypse.');
      return token.text;
    }
    const transformed = numericMode === 'common'
      ? commonInteger(parsed.value, parsed.suffix)
      : fullInteger(parsed.value, parsed.suffix);
    if (!transformed) return token.text;
    integerCount += 1;
    return transformed;
  }).join('');

  if (skippedNumberCount > 0 && numericMode !== 'off') {
    warnings.add(`${skippedNumberCount} floating-point or user-defined numeric literal(s) were preserved.`);
  }
  if (renameIdentifiers && mapping.size > 0) {
    warnings.add('External APIs, judge-required function names, and reflection may need the preserve list.');
  }

  return {
    code: output,
    mapping: Object.fromEntries(mapping),
    stats: {
      renamedIdentifiers: mapping.size,
      transformedIntegers: integerCount,
      expansionPercent: source.length ? Math.round((output.length / source.length) * 100) : 100,
    },
    warnings: [...warnings],
  };
}
