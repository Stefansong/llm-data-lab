# Frontend Architecture Recommendations

## Current Structure Issues

### 1. WorkspaceClient.tsx is Too Large (1017 lines)

**Current**: Single monolithic component handling:
- State management (30+ state variables)
- File uploads
- Code generation
- Code execution
- Chat interface
- Provider configuration
- Data transformation

**Recommended Refactor**:

```
components/workspace/
├── WorkspaceClient.tsx          # Main layout component (300 lines)
├── TaskInputSection.tsx         # Task description + model selection (150 lines)
├── CodePanel.tsx               # Code editor + execution (250 lines)
├── ChatPanel.tsx               # Already exists, already good
├── DatasetSection.tsx          # Dataset upload + preview (200 lines)
├── ExecutionResultsPanel.tsx   # Results display (150 lines)
└── hooks/
    ├── useWorkspaceState.ts    # Complex state management
    ├── useCodeGeneration.ts    # Code generation logic
    ├── useCodeExecution.ts     # Code execution logic
    └── useChatSession.ts       # Chat session management
```

### 2. State Management Issues

**Current**: Many hooks at component level
```typescript
// BAD - 30+ hooks in WorkspaceClient
const [prompt, setPrompt] = useState(...);
const [taskType, setTaskType] = useState(...);
const [model, setModel] = useState(...);
const [code, setCode] = useState(...);
const [dataset, setDataset] = useState(...);
// ... many more
```

**Recommended**: Use custom hooks to group related state
```typescript
// GOOD - organize by feature
function useWorkspaceState() {
  const [prompt, setPrompt] = useState(...);
  const [taskType, setTaskType] = useState(...);
  return { prompt, setPrompt, taskType, setTaskType };
}

function useCodeGeneration() {
  const [code, setCode] = useState(...);
  const [isGenerating, setIsGenerating] = useState(...);
  return { code, setCode, isGenerating, setIsGenerating };
}

// In component:
function WorkspaceClient() {
  const workspaceState = useWorkspaceState();
  const codeGen = useCodeGeneration();
  // ... cleaner component
}
```

### 3. Missing Error Boundary

**Current**: No error handling for component crashes

**Recommended**:
```typescript
// components/ErrorBoundary.tsx
export class ErrorBoundary extends React.Component {
  state = { hasError: false };
  
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  
  render() {
    if (this.state.hasError) {
      return <FallbackUI />;
    }
    return this.props.children;
  }
}

// app/workspace/page.tsx
<ErrorBoundary>
  <WorkspaceClient />
</ErrorBoundary>
```

### 4. Add Reusable Components

**Missing UI Components**:
- Button.tsx (consolidate button styles)
- LoadingSpinner.tsx
- SkeletonLoader.tsx
- FormField.tsx (with validation)
- Modal.tsx (accessibility-first)
- ConfirmDialog.tsx

Example:
```typescript
// components/ui/Button.tsx
export function Button({
  variant = 'primary',
  disabled = false,
  loading = false,
  children,
  ...props
}: ButtonProps) {
  const variants = {
    primary: 'bg-brand hover:bg-brand-light',
    secondary: 'border border-slate-700',
    danger: 'bg-rose-500 hover:bg-rose-600',
  };
  return (
    <button
      className={`... ${variants[variant]}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}
```

### 5. Type Safety Issues

**Current**: Some API responses parsed without validation

**Recommended**: Use Zod for schema validation
```typescript
import { z } from 'zod';

const DatasetUploadSchema = z.object({
  filename: z.string(),
  original_filename: z.string(),
  columns: z.array(z.string()),
  schema: z.record(z.string()),
  preview: z.array(z.record(z.unknown())),
  rows: z.number(),
});

type DatasetUpload = z.infer<typeof DatasetUploadSchema>;

// In API:
export async function uploadDataset(file: File): Promise<DatasetUpload> {
  const response = await fetch(...);
  const data = await response.json();
  return DatasetUploadSchema.parse(data); // Throws if invalid
}
```

### 6. Add Form Validation Library

**Recommended**: React Hook Form + Zod
```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const AuthSchema = z.object({
  username: z.string().min(1, 'Required'),
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Min 8 characters'),
});

function AuthForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(AuthSchema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
    </form>
  );
}
```

### 7. Improve i18n Structure

**Current**: Massive i18n.ts file with all text

**Recommended**: Organize by feature
```
lib/i18n/
├── auth.ts     # Auth-related text
├── workspace.ts
├── history.ts
├── settings.ts
├── common.ts   # Shared text
└── index.ts    # Exports
```

### 8. Add Utility Modules

Extract complex logic from components:

```
lib/
├── api.ts            # Existing
├── authToken.ts      # Existing
├── userProfile.ts    # Existing
├── providerSettings.ts # Existing
├── validators.ts     # NEW - form validation functions
├── errorHandling.ts  # NEW - error mapping and handling
├── storage.ts        # NEW - localStorage utilities with types
├── date.ts          # NEW - date formatting utilities
└── diff.ts          # NEW - diff/patch utilities (extract from workspace)
```

Example errorHandling.ts:
```typescript
export type ErrorType = 'network' | 'auth' | 'validation' | 'server' | 'unknown';

export function classifyError(error: Error): ErrorType {
  if (!navigator.onLine) return 'network';
  const msg = error.message;
  if (msg.includes('401')) return 'auth';
  if (msg.includes('400')) return 'validation';
  if (msg.includes('5')) return 'server';
  return 'unknown';
}

export function getErrorMessage(error: Error, lang: Lang): string {
  const type = classifyError(error);
  const messages = {
    zh: {
      network: 'Network connection failed',
      auth: 'Authentication failed',
      // ...
    },
    en: { /* ... */ }
  };
  return messages[lang][type];
}
```

### 9. Add TypeScript Strict Mode

**Current**: tsconfig likely has some relaxed settings

**Recommended**:
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true
  }
}
```

### 10. Add Testing

**Missing**: No test files found

**Recommended**:
```
components/
├── workspace/
│   ├── WorkspaceClient.tsx
│   ├── WorkspaceClient.test.tsx
│   └── TaskInputSection.test.tsx
└── ...
```

Use Jest + React Testing Library:
```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { AuthClient } from './AuthClient';

describe('AuthClient', () => {
  it('shows error for empty fields', () => {
    render(<AuthClient />);
    fireEvent.click(screen.getByText('登录'));
    expect(screen.getByText(/请输入用户名和密码/)).toBeInTheDocument();
  });
});
```

### 11. Add Storybook for Component Documentation

**Setup**:
```bash
npx storybook@latest init
```

Example story:
```typescript
// components/ui/Button.stories.tsx
import { Button } from './Button';

export default {
  component: Button,
  tags: ['autodocs'],
};

export const Primary = {
  args: { children: 'Click me', variant: 'primary' },
};

export const Loading = {
  args: { children: 'Click me', loading: true },
};
```

---

## Migration Path

### Week 1: Setup
- [ ] Add Zod for validation
- [ ] Setup ErrorBoundary
- [ ] Create reusable UI components (Button, Modal, etc.)

### Week 2: Refactor WorkspaceClient
- [ ] Extract TaskInputSection.tsx
- [ ] Extract DatasetSection.tsx
- [ ] Extract CodePanel.tsx
- [ ] Extract ExecutionResultsPanel.tsx

### Week 3: State Management
- [ ] Create useWorkspaceState hook
- [ ] Create useCodeGeneration hook
- [ ] Create useCodeExecution hook
- [ ] Create useChatSession hook

### Week 4: Quality
- [ ] Add form validation with React Hook Form
- [ ] Add Error Boundary
- [ ] Add 50+ unit tests
- [ ] Add Storybook stories

### Week 5: Polish
- [ ] Add loading skeletons
- [ ] Improve error messages
- [ ] Add TypeScript strict mode
- [ ] Fix accessibility issues

---

## File Organization Proposal

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── auth/
│   │   └── page.tsx
│   ├── workspace/
│   │   └── page.tsx
│   ├── history/
│   │   └── page.tsx
│   ├── settings/
│   │   └── page.tsx
│   └── globals.css
├── components/
│   ├── ui/              # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Modal.tsx
│   │   ├── FormField.tsx
│   │   ├── Spinner.tsx
│   │   ├── Skeleton.tsx
│   │   ├── Alert.tsx    # Exists
│   │   └── Button.test.tsx
│   ├── layout/
│   │   ├── AppShell.tsx # Exists
│   │   └── AppShell.test.tsx
│   ├── auth/
│   │   ├── AuthClient.tsx   # Exists
│   │   ├── AuthGuard.tsx    # Exists
│   │   └── AuthClient.test.tsx
│   ├── workspace/
│   │   ├── WorkspaceClient.tsx
│   │   ├── TaskInputSection.tsx       # NEW
│   │   ├── DatasetSection.tsx         # NEW
│   │   ├── CodePanel.tsx              # NEW
│   │   ├── ExecutionResultsPanel.tsx  # NEW
│   │   ├── ChatPanel.tsx              # Exists
│   │   └── *.test.tsx
│   ├── history/
│   │   ├── HistoryClient.tsx  # Exists
│   │   └── HistoryClient.test.tsx
│   └── settings/
│       ├── SettingsClient.tsx # Exists
│       └── SettingsClient.test.tsx
├── hooks/                 # NEW: Custom hooks
│   ├── useWorkspaceState.ts
│   ├── useCodeGeneration.ts
│   ├── useCodeExecution.ts
│   ├── useChatSession.ts
│   └── *.test.ts
├── lib/
│   ├── api.ts           # Exists
│   ├── authToken.ts     # Exists
│   ├── userProfile.ts   # Exists
│   ├── providerSettings.ts # Exists
│   ├── i18n/            # REORGANIZED
│   │   ├── auth.ts
│   │   ├── workspace.ts
│   │   ├── history.ts
│   │   ├── settings.ts
│   │   ├── common.ts
│   │   └── index.ts
│   ├── validators.ts    # NEW
│   ├── errorHandling.ts # NEW
│   ├── storage.ts       # NEW
│   └── date.ts          # NEW
├── types/               # NEW: Shared types
│   ├── api.ts
│   ├── workspace.ts
│   └── index.ts
├── __tests__/          # Test utilities
│   └── setup.ts
├── tailwind.config.js
├── tsconfig.json
├── package.json
└── next.config.js
```

---

## Performance Considerations

1. **Code Splitting**: Already using dynamic imports for Monaco Editor - good!
2. **Bundle Size**: Monitor component size with `next/bundle-analyzer`
3. **Re-renders**: Use React DevTools profiler to find unnecessary re-renders
4. **Images**: Optimize any image assets with next/image
5. **API Calls**: Consider SWR for data fetching (already in package.json but not used)

---

## Dependencies to Consider Adding

```json
{
  "react-hook-form": "^7.x",
  "zod": "^3.x",
  "@hookform/resolvers": "^3.x",
  "zustand": "^4.x",
  "react-hot-toast": "^2.x"
}
```

