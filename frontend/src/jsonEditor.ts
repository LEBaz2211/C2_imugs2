const INDENT = "  ";

export type JsonEditorEdit = {
  value: string;
  selectionStart: number;
  selectionEnd: number;
};

export function editJsonForKey(value: string, selectionStart: number, selectionEnd: number, key: string, shiftKey = false): JsonEditorEdit | undefined {
  if (key === "Enter") return insertSmartNewline(value, selectionStart, selectionEnd);
  if (key === "Tab") return shiftKey ? unindent(value, selectionStart, selectionEnd) : indent(value, selectionStart, selectionEnd);
  if (key === "Backspace") return removeEmptyPair(value, selectionStart, selectionEnd);
  if ((key === "{" || key === "[") && !isInsideString(value, selectionStart)) return insertPair(value, selectionStart, selectionEnd, key, key === "{" ? "}" : "]");
  if (key === '"') return insertQuote(value, selectionStart, selectionEnd);
  if ((key === "}" || key === "]") && selectionStart === selectionEnd && !isInsideString(value, selectionStart) && value[selectionStart] === key) {
    return { value, selectionStart: selectionStart + 1, selectionEnd: selectionStart + 1 };
  }
  return undefined;
}

export function jsonCursorPosition(value: string, offset: number) {
  const safeOffset = Math.max(0, Math.min(offset, value.length));
  const before = value.slice(0, safeOffset);
  const lastNewline = before.lastIndexOf("\n");
  return {
    line: before.split("\n").length,
    column: safeOffset - lastNewline,
  };
}

function insertSmartNewline(value: string, start: number, end: number): JsonEditorEdit {
  const before = value.slice(0, start);
  const after = value.slice(end);
  const previous = lastNonWhitespace(before);
  const next = firstNonWhitespace(after);
  const depth = nestingDepth(before);
  const opensBlock = previous === "{" || previous === "[";
  const afterColon = previous === ":";
  const betweenPair = (previous === "{" && next === "}") || (previous === "[" && next === "]");
  const innerDepth = Math.max(0, depth + (afterColon ? 1 : 0));
  const innerIndent = INDENT.repeat(innerDepth);

  if (betweenPair) {
    const closingIndent = INDENT.repeat(Math.max(0, depth - 1));
    const inserted = `\n${innerIndent}\n${closingIndent}`;
    const cursor = before.length + 1 + innerIndent.length;
    return { value: before + inserted + after, selectionStart: cursor, selectionEnd: cursor };
  }

  const targetDepth = opensBlock ? depth : innerDepth;
  const indentation = INDENT.repeat(Math.max(0, targetDepth));
  const inserted = `\n${indentation}`;
  const cursor = before.length + inserted.length;
  return { value: before + inserted + after, selectionStart: cursor, selectionEnd: cursor };
}

function indent(value: string, start: number, end: number): JsonEditorEdit {
  if (start === end) {
    const lineStart = value.lastIndexOf("\n", start - 1) + 1;
    const column = start - lineStart;
    const spaces = INDENT.length - (column % INDENT.length);
    const inserted = " ".repeat(spaces);
    const cursor = start + spaces;
    return {
      value: value.slice(0, start) + inserted + value.slice(end),
      selectionStart: cursor,
      selectionEnd: cursor,
    };
  }

  const range = selectedLineRange(value, start, end);
  const block = value.slice(range.start, range.end);
  const indented = block.split("\n").map((line) => `${INDENT}${line}`).join("\n");
  return {
    value: value.slice(0, range.start) + indented + value.slice(range.end),
    selectionStart: range.start,
    selectionEnd: range.start + indented.length,
  };
}

function unindent(value: string, start: number, end: number): JsonEditorEdit | undefined {
  const range = selectedLineRange(value, start, end);
  const block = value.slice(range.start, range.end);
  let changed = false;
  const unindented = block
    .split("\n")
    .map((line) => {
      if (line.startsWith(INDENT)) {
        changed = true;
        return line.slice(INDENT.length);
      }
      if (line.startsWith(" ") || line.startsWith("\t")) {
        changed = true;
        return line.slice(1);
      }
      return line;
    })
    .join("\n");
  if (!changed) return undefined;

  const nextValue = value.slice(0, range.start) + unindented + value.slice(range.end);
  if (start === end) {
    const removed = block.length - unindented.length;
    const cursor = Math.max(range.start, start - removed);
    return { value: nextValue, selectionStart: cursor, selectionEnd: cursor };
  }
  return {
    value: nextValue,
    selectionStart: range.start,
    selectionEnd: range.start + unindented.length,
  };
}

function insertPair(value: string, start: number, end: number, opening: string, closing: string): JsonEditorEdit {
  const selected = value.slice(start, end);
  const replacement = `${opening}${selected}${closing}`;
  const cursorStart = start + 1;
  return {
    value: value.slice(0, start) + replacement + value.slice(end),
    selectionStart: cursorStart,
    selectionEnd: end > start ? cursorStart + selected.length : cursorStart,
  };
}

function insertQuote(value: string, start: number, end: number): JsonEditorEdit | undefined {
  if (start === end && value[start] === '"') {
    return { value, selectionStart: start + 1, selectionEnd: start + 1 };
  }
  if (isEscaped(value, start)) return undefined;
  if (start === end && isInsideString(value, start)) {
    const cursor = start + 1;
    return {
      value: value.slice(0, start) + '"' + value.slice(end),
      selectionStart: cursor,
      selectionEnd: cursor,
    };
  }
  return insertPair(value, start, end, '"', '"');
}

function removeEmptyPair(value: string, start: number, end: number): JsonEditorEdit | undefined {
  if (start !== end || start === 0) return undefined;
  const pair = `${value[start - 1] ?? ""}${value[start] ?? ""}`;
  if (!["{}", "[]", '""'].includes(pair)) return undefined;
  return {
    value: value.slice(0, start - 1) + value.slice(start + 1),
    selectionStart: start - 1,
    selectionEnd: start - 1,
  };
}

function selectedLineRange(value: string, start: number, end: number) {
  const rangeStart = value.lastIndexOf("\n", start - 1) + 1;
  const effectiveEnd = end > start && value[end - 1] === "\n" ? end - 1 : end;
  const newline = value.indexOf("\n", effectiveEnd);
  return { start: rangeStart, end: newline < 0 ? value.length : newline };
}

function nestingDepth(value: string) {
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (const character of value) {
    if (inString) {
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === '"') inString = false;
      continue;
    }
    if (character === '"') inString = true;
    else if (character === "{" || character === "[") depth += 1;
    else if (character === "}" || character === "]") depth = Math.max(0, depth - 1);
  }
  return depth;
}

function isEscaped(value: string, offset: number) {
  let slashCount = 0;
  for (let index = offset - 1; index >= 0 && value[index] === "\\"; index -= 1) slashCount += 1;
  return slashCount % 2 === 1;
}

function isInsideString(value: string, offset: number) {
  let inString = false;
  let escaped = false;
  for (const character of value.slice(0, offset)) {
    if (escaped) {
      escaped = false;
      continue;
    }
    if (character === "\\" && inString) escaped = true;
    else if (character === '"') inString = !inString;
  }
  return inString;
}

function lastNonWhitespace(value: string) {
  return value.trimEnd().slice(-1);
}

function firstNonWhitespace(value: string) {
  return value.trimStart()[0];
}
