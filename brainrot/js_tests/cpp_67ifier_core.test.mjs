import assert from 'node:assert/strict';
import test from 'node:test';

import {tokenizeCpp, transformCpp} from '../static/brainrot/cpp_67ifier_core.mjs';

test('preserves comments, quoted literals, raw strings, and preprocessor directives', () => {
  const source = `#define LIMIT 67
// value should stay 67 here
const char* label = "value 67";
auto raw = R"tag(value 67)tag";
int value = LIMIT;`;
  const result = transformCpp(source, {numericMode: 'common'});

  assert.match(result.code, /^#define LIMIT 67/m);
  assert.match(result.code, /\/\/ value should stay 67 here/);
  assert.match(result.code, /"value 67"/);
  assert.match(result.code, /R"tag\(value 67\)tag"/);
  assert.match(result.code, /LIMIT/);
  assert.equal(result.mapping.value, 'sixone');
});

test('renames user identifiers consistently and preserves common C++ names', () => {
  const source = 'int main(){ std::vector<int> values; values.push_back(6); return values.size(); }';
  const result = transformCpp(source, {numericMode: 'off'});

  assert.equal(result.mapping.values, 'sixseven');
  assert.equal(result.code.match(/sixseven/g).length, 3);
  assert.match(result.code, /int main\(\)/);
  assert.match(result.code, /std::vector/);
  assert.match(result.code, /push_back/);
});

test('honours the preserve list and conservatively keeps underscore names', () => {
  const source = 'int solve(int grader_value, int _abi_name) { return grader_value + _abi_name; }';
  const result = transformCpp(source, {
    numericMode: 'off',
    preservedNames: 'solve, grader_value',
  });

  assert.equal(result.code, source);
  assert.deepEqual(result.mapping, {});
});

test('common mode changes themed integer specimens but not floating point', () => {
  const source = 'auto a=0; auto b=67ULL; auto c=3.14;';
  const result = transformCpp(source, {renameIdentifiers: false, numericMode: 'common'});

  assert.match(result.code, /\(67 \^ 67\)/);
  assert.match(result.code, /\(61ULL \+ 6ULL\)/);
  assert.match(result.code, /3\.14/);
  assert.equal(result.stats.transformedIntegers, 2);
});

test('full mode rewrites arbitrary supported integers with logarithmic Horner expressions', () => {
  const result = transformCpp('int answer = 42;', {renameIdentifiers: false, numericMode: 'all'});

  assert.doesNotMatch(result.code, /\b42\b/);
  assert.match(result.code, /7 - 6/);
  assert.match(result.code, /int answer = \(/);
  assert.equal(result.stats.transformedIntegers, 1);
});

test('tokenizer does not split prefixed and raw literals', () => {
  const literalTokens = tokenizeCpp('auto a=u8"67"; auto b=LR"x(61)x";')
    .filter((token) => token.type === 'literal')
    .map((token) => token.text);

  assert.deepEqual(literalTokens, ['u8"67"', 'LR"x(61)x"']);
});
