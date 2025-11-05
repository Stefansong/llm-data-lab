# Frontend UX/UI Issues - Quick Reference

## Critical Issues (Fix First)

### 1. Hardcoded Chinese Text - AuthGuard.tsx:37
```typescript
// WRONG - hardcoded Chinese, breaks i18n
正在校验登录状态...

// CORRECT - use i18n
const [lang, setLang] = useState<Lang>("zh");
// Add to i18n: authTexts.zh.verifying = "正在校验登录状态..."
```
**Impact**: Non-Chinese users see untranslated UI

---

### 2. Generic Error Messages - AuthClient.tsx:60-68, WorkspaceClient.tsx:496-497
```typescript
// WRONG - shows raw error to user
catch (err) {
  setError(err instanceof Error ? err.message : String(err));
}

// CORRECT - map to user-friendly message
const errorMap = {
  'Unauthorized': 'Invalid username or password',
  'Network Error': 'Connection failed. Please check your internet.',
  'Server Error': 'Server error. Please try again later.'
};
```
**Impact**: Users confused, raw API errors exposed

---

### 3. No Form Validation - AuthClient.tsx:37-44, SettingsClient.tsx:154-189
```typescript
// WRONG - no validation
if (!username || !password) {
  setError(T.needUserPass);
  return;
}

// CORRECT - validate format
const validateEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
const validatePassword = (pwd: string) => pwd.length >= 8;
const validateUrl = (url: string) => {
  try { new URL(url); return true; } catch { return false; }
};
```
**Impact**: Invalid data submitted, poor UX

---

### 4. No Loading Indicators - HistoryClient.tsx:170-254, ChatPanel.tsx:143
```typescript
// WRONG - just text
{isDetailLoading ? <Alert tone="info" message={T.loading} /> : null}
{isLoading ? <p className="text-xs text-brand">{T.thinking}</p> : null}

// CORRECT - add spinner
import { Loader2 } from 'lucide-react';
{isLoading && <Loader2 className="animate-spin" />}
// Or skeleton: <Skeleton className="h-20 w-full" />
```
**Impact**: App appears frozen

---

### 5. Accessibility Missing - All components
```typescript
// WRONG - no labels, no roles
<input type="password" value={form.apiKey} />
<div className="fixed inset-0 z-40 flex items-center">

// CORRECT - proper ARIA
<label htmlFor="apiKey">API Key</label>
<input id="apiKey" type="password" aria-required="true" />
<div role="dialog" aria-modal="true" aria-labelledby="title">
  <h2 id="title">Dialog Title</h2>
</div>
```
**Impact**: Non-accessible for screen readers

---

## Medium Issues (Fix Next)

### 6. WorkspaceClient Too Large - 1017 lines
**Current**: One massive component  
**Fix**: Split into:
- TaskInputSection.tsx
- CodeGenerationPanel.tsx
- ExecutionPanel.tsx
- ChatCopilocPanel.tsx

---

### 7. No Unsaved Work Persistence
```typescript
// Add auto-save
useEffect(() => {
  const timer = setTimeout(() => {
    localStorage.setItem('workspace.prompt', prompt);
    localStorage.setItem('workspace.code', code);
  }, 1000);
  return () => clearTimeout(timer);
}, [prompt, code]);

// Restore on load
useEffect(() => {
  const saved = localStorage.getItem('workspace.prompt');
  if (saved) setPrompt(saved);
}, []);
```

---

### 8. Modal Accessibility - HistoryClient.tsx:170-254
```typescript
// MISSING: role, aria-modal, focus trap
// ADD:
import { useRef, useEffect } from 'react';

<div role="dialog" aria-modal="true" aria-labelledby="dialogTitle">
  <h2 id="dialogTitle">{T.task}</h2>
  {/* content */}
</div>
```

---

### 9. Dataset Preview Limitations
**Current**: Shows only first 20 rows, fixed height  
**Fix**:
- Add pagination or "Load more" button
- Dynamic height or better scrolling
- Column sorting
- Search/filter capability

---

### 10. Poor Responsive Design
**Issue**: Only 13 breakpoint usages, mobile untested  
**Test on**:
- Mobile (320px)
- Tablet (768px)
- Desktop (1024px+)

Focus areas:
- Code editor on small screens
- Chat panel responsiveness
- Modal on narrow screens
- Data preview table overflow

---

## Low Priority Issues

### 11. No Copy-to-Clipboard
```typescript
// Add to code blocks
<button onClick={() => navigator.clipboard.writeText(code)}>
  Copy code
</button>
```

### 12. No Loading Skeletons
```typescript
// Replace simple loading text
{isLoading ? <Skeleton count={5} /> : <TaskList tasks={tasks} />}
```

### 13. No Pagination for History
```typescript
// Current: limit=20, no offset
// Add: offset parameter, "Load more" button
const [offset, setOffset] = useState(0);
const handleLoadMore = () => setOffset(o => o + 20);
```

### 14. Chat Message Overflow
```typescript
// Add overflow handling
<p className="whitespace-pre-wrap break-words overflow-hidden">
  {contentText}
</p>
```

---

## File Quick Lookup

| Issue | File | Lines |
|-------|------|-------|
| Hardcoded Chinese | AuthGuard.tsx | 37 |
| Generic errors | AuthClient.tsx | 60-68 |
| Generic errors | WorkspaceClient.tsx | 496-497 |
| No validation | AuthClient.tsx | 37-44 |
| No validation | SettingsClient.tsx | 154-189 |
| No spinners | HistoryClient.tsx | 170-254 |
| No spinners | ChatPanel.tsx | 143 |
| Complex component | WorkspaceClient.tsx | 1-1017 |
| No persistence | WorkspaceClient.tsx | 733-736 |
| Dataset preview | WorkspaceClient.tsx | 855-893 |
| Modal a11y | HistoryClient.tsx | 170-254 |
| Chat parsing | ChatPanel.tsx | 81-113 |
| Memory leak | providerSettings.ts | 13-20 |
| No pagination | HistoryClient.tsx | 280-283 |

---

## Testing Checklist

- [ ] All form inputs validated
- [ ] All error messages user-friendly
- [ ] All interactive elements have aria-labels
- [ ] Modal trap focus and support ESC key
- [ ] Loading states show spinners
- [ ] Empty states show guidance
- [ ] Responsive on mobile, tablet, desktop
- [ ] Chat doesn't overflow horizontally
- [ ] Dataset preview works with large files
- [ ] No console errors on page load
- [ ] Copy buttons work
- [ ] Unsaved work persists on reload
