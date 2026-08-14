import {transformCpp} from './cpp_67ifier_core.mjs?v=20260814.1';

const input = document.getElementById('cpp67-input');
const output = document.getElementById('cpp67-output');
const rename = document.getElementById('cpp67-rename');
const numberMode = document.getElementById('cpp67-number-mode');
const preserve = document.getElementById('cpp67-preserve');
const transformButton = document.getElementById('cpp67-transform');
const copyButton = document.getElementById('cpp67-copy');
const downloadButton = document.getElementById('cpp67-download');
const sampleButton = document.getElementById('cpp67-sample');
const resetButton = document.getElementById('cpp67-reset');
const nameCount = document.getElementById('cpp67-name-count');
const integerCount = document.getElementById('cpp67-integer-count');
const expansion = document.getElementById('cpp67-expansion');
const status = document.getElementById('cpp67-status');

const sample = `#include <bits/stdc++.h>
using namespace std;

// The string and this comment must remain exactly as written.
long long solve(vector<int> values) {
    long long answer = 0;
    for (int index = 0; index < (int)values.size(); ++index) {
        if (values[index] == 67) answer += values[index] * 6;
    }
    cout << "SIX SEVEN: " << answer << '\\n';
    return answer + 61;
}

int main() {
    vector<int> data = {6, 7, 61, 67};
    cout << solve(data) << '\\n';
}`;

function renderResult(result) {
  output.value = result.code;
  nameCount.textContent = result.stats.renamedIdentifiers;
  integerCount.textContent = result.stats.transformedIntegers;
  expansion.textContent = `${result.stats.expansionPercent}%`;
  status.textContent = result.warnings.length
    ? result.warnings.join(' ')
    : 'Transformation complete. The Institute found no paperwork to add.';
}

function transform() {
  renderResult(transformCpp(input.value, {
    renameIdentifiers: rename.checked,
    numericMode: numberMode.value,
    preservedNames: preserve.value,
  }));
}

async function copyOutput() {
  if (!output.value) transform();
  try {
    await navigator.clipboard.writeText(output.value);
  } catch {
    output.focus();
    output.select();
    document.execCommand('copy');
  }
  status.textContent = 'Peer-reviewed source copied to clipboard.';
}

function downloadOutput() {
  if (!output.value) transform();
  const url = URL.createObjectURL(new Blob([output.value], {type: 'text/x-c++src;charset=utf-8'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'six-seven.cpp';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
  status.textContent = 'six-seven.cpp has escaped the laboratory.';
}

transformButton.addEventListener('click', transform);
copyButton.addEventListener('click', copyOutput);
downloadButton.addEventListener('click', downloadOutput);
sampleButton.addEventListener('click', () => {
  input.value = sample;
  transform();
});
resetButton.addEventListener('click', () => {
  input.value = '';
  output.value = '';
  nameCount.textContent = '0';
  integerCount.textContent = '0';
  expansion.textContent = '100%';
  status.textContent = 'Awaiting a scientifically unnecessary program.';
  input.focus();
});

input.value = sample;
transform();
