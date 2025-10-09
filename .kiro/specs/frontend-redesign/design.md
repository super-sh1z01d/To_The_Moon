# Design Document: Frontend Redesign

## Overview

This document outlines the technical design for a complete frontend redesign of the To The Moon application. The redesign focuses on modern UI/UX with shadcn/ui, performance optimization with TanStack Query, and comprehensive data visualization.

## Architecture

### Technology Stack

**Core Framework:**
- React 18.2+ with TypeScript 5.5+
- Vite 5.4+ for build tooling
- React Router DOM 6.26+ for routing

**UI Layer:**
- shadcn/ui components
- Tailwind CSS 3.4+ for styling
- Radix UI primitives (via shadcn/ui)
- Lucide React for icons

**Data Management:**
- TanStack Query (React Query) v5 for server state
- Zustand for client state (if needed)
- TanStack Virtual for list virtualization

**Data Visualization:**
- Recharts for charts and graphs
- Custom components for metrics display

**Forms & Validation:**
- React Hook Form for form management
- Zod for schema validation

**Utilities:**
- clsx + tailwind-merge for className management
- date-fns for date formatting
- lodash-es for utility functions (debounce, throttle)

### Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── table.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ...
│   │   ├── layout/          # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── ThemeToggle.tsx
│   │   │   └── MobileNav.tsx
│   │   ├── tokens/          # Token-specific components
│   │   │   ├── TokenTable.tsx
│   │   │   ├── TokenCard.tsx
│   │   │   ├── TokenFilters.tsx
│   │   │   └── TokenMetrics.tsx
│   │   ├── charts/          # Chart components
│   │   │   ├── PriceChart.tsx
│   │   │   ├── LiquidityChart.tsx
│   │   │   ├── VolumeChart.tsx
│   │   │   └── ScoreBreakdown.tsx
│   │   └── settings/        # Settings components
│   │       ├── SettingsGroup.tsx
│   │       ├── SettingField.tsx
│   │       └── SettingsSearch.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── TokenDetail.tsx
│   │   ├── Settings.tsx
│   │   ├── Monitoring.tsx
│   │   └── Logs.tsx
│   ├── hooks/               # Custom hooks
│   │   ├── useTokens.ts
│   │   ├── useTokenDetail.ts
│   │   ├── useSettings.ts
│   │   ├── useTheme.ts
│   │   └── useDebounce.ts
│   ├── lib/
│   │   ├── api.ts           # API client
│   │   ├── queryClient.ts   # React Query config
│   │   ├── utils.ts         # Utility functions
│   │   └── constants.ts     # Constants
│   ├── types/
│   │   ├── token.ts
│   │   ├── settings.ts
│   │   └── api.ts
│   ├── styles/
│   │   └── globals.css      # Global styles + Tailwind
│   ├── App.tsx
│   └── main.tsx
├── components.json          # shadcn/ui config
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## Components and Interfaces

### Core Components

#### 1. Layout Components

**Header Component:**
```typescript
interface HeaderProps {
  title: string;
  actions?: React.ReactNode;
}

// Features:
// - App title/logo
// - Navigation links
// - Theme toggle
// - Mobile menu trigger
```

**Sidebar Component:**
```typescript
interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

// Features:
// - Navigation menu
// - Active route highlighting
// - Collapsible on mobile
```

#### 2. Token Components

**TokenTable Component:**
```typescript
interface TokenTableProps {
  tokens: Token[];
  isLoading: boolean;
  onSort: (column: string) => void;
  sortColumn: string;
  sortDirection: 'asc' | 'desc';
}

// Features:
// - Virtualized rows (TanStack Virtual)
// - Sortable columns
// - Click to navigate to detail
// - Responsive (cards on mobile)
```

**TokenFilters Component:**
```typescript
interface TokenFiltersProps {
  filters: TokenFilters;
  onFilterChange: (filters: TokenFilters) => void;
}

interface TokenFilters {
  status?: 'active' | 'monitoring' | 'archived';
  minScore?: number;
  maxSpam?: number;
  search?: string;
}

// Features:
// - Debounced search input
// - Status dropdown
// - Score range slider
// - Spam percentage filter
```

#### 3. Chart Components

**PriceChart Component:**
```typescript
interface PriceChartProps {
  data: PriceDataPoint[];
  timeframe: '5m' | '15m' | '1h';
  isDark: boolean;
}

interface PriceDataPoint {
  timestamp: string;
  price: number;
  delta: number;
}

// Uses Recharts LineChart
```

**ScoreBreakdown Component:**
```typescript
interface ScoreBreakdownProps {
  components: ScoreComponents;
  weights: ScoreWeights;
}

interface ScoreComponents {
  tx_accel: number;
  vol_momentum: number;
  freshness: number;
  orderflow: number;
}

// Uses Recharts BarChart
```

#### 4. Settings Components

**SettingsGroup Component:**
```typescript
interface SettingsGroupProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  collapsible?: boolean;
}

// Features:
// - Collapsible sections
// - Clear grouping
// - Descriptions
```

**SettingField Component:**
```typescript
interface SettingFieldProps {
  setting: Setting;
  value: string;
  onChange: (value: string) => void;
  onSave: () => void;
}

interface Setting {
  key: string;
  label: string;
  description: string;
  type: 'number' | 'text' | 'boolean' | 'select';
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
}

// Features:
// - Type-specific inputs
// - Validation
// - Save button with loading state
// - Error display
```

## Data Models

### Token Model

```typescript
interface Token {
  mint_address: string;
  name: string | null;
  symbol: string | null;
  status: 'active' | 'monitoring' | 'archived';
  score: number;
  liquidity_usd: number;
  delta_p_5m: number;
  delta_p_15m: number;
  n_5m: number;
  primary_dex: string;
  fetched_at: string;
  scored_at: string;
  last_processed_at: string;
  solscan_url: string;
  raw_components: ScoreComponents;
  spam_metrics?: SpamMetrics;
}

interface SpamMetrics {
  spam_percentage: number;
  risk_level: 'low' | 'medium' | 'high';
  compute_budget_ratio: number;
  transactions_analyzed: number;
}

interface ScoreComponents {
  tx_accel: number;
  vol_momentum: number;
  freshness: number;
  orderflow_imbalance: number;
}
```

### Settings Model

```typescript
interface Setting {
  key: string;
  value: string;
}

interface SettingsMap {
  [key: string]: string;
}

interface SettingDefinition {
  key: string;
  label: string;
  description: string;
  category: string;
  type: 'number' | 'text' | 'boolean' | 'textarea';
  min?: number;
  max?: number;
  step?: number;
  defaultValue: string;
}
```

## Data Flow & State Management

### React Query Configuration

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,           // Data fresh for 5 seconds
      cacheTime: 10 * 60 * 1000, // Cache for 10 minutes
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 1,
    },
  },
});
```

### Custom Hooks

**useTokens Hook:**
```typescript
function useTokens(filters: TokenFilters) {
  return useQuery({
    queryKey: ['tokens', filters],
    queryFn: () => fetchTokens(filters),
    staleTime: 5000,
    refetchInterval: 10000, // Auto-refresh every 10s
  });
}
```

**useTokenDetail Hook:**
```typescript
function useTokenDetail(mintAddress: string) {
  return useQuery({
    queryKey: ['token', mintAddress],
    queryFn: () => fetchTokenDetail(mintAddress),
    staleTime: 3000,
    refetchInterval: 5000, // Auto-refresh every 5s
  });
}
```

**useSettings Hook:**
```typescript
function useSettings() {
  const queryClient = useQueryClient();
  
  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: fetchAllSettings,
  });
  
  const updateSetting = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      updateSettingAPI(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });
  
  return { settings, updateSetting };
}
```

## Theme System

### Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        // ... shadcn/ui color system
      },
    },
  },
};
```

### Theme Provider

```typescript
interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: 'light' | 'dark' | 'system';
}

// Features:
// - Detect system preference
// - Persist theme choice
// - Provide theme context
// - Handle theme transitions
```

## Performance Optimizations

### 1. Virtualization

```typescript
// Token table with virtualization
import { useVirtualizer } from '@tanstack/react-virtual';

function TokenTable({ tokens }: { tokens: Token[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  
  const virtualizer = useVirtualizer({
    count: tokens.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60, // Row height
    overscan: 5, // Render 5 extra rows
  });
  
  // Only render visible rows
}
```

### 2. Debouncing

```typescript
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => clearTimeout(handler);
  }, [value, delay]);
  
  return debouncedValue;
}

// Usage in search
const [search, setSearch] = useState('');
const debouncedSearch = useDebounce(search, 300);

useTokens({ search: debouncedSearch });
```

### 3. Code Splitting

```typescript
// Lazy load pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const TokenDetail = lazy(() => import('./pages/TokenDetail'));
const Settings = lazy(() => import('./pages/Settings'));

// With Suspense
<Suspense fallback={<PageLoader />}>
  <Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/token/:id" element={<TokenDetail />} />
    <Route path="/settings" element={<Settings />} />
  </Routes>
</Suspense>
```

### 4. Memoization

```typescript
// Memoize expensive calculations
const sortedTokens = useMemo(() => {
  return tokens.sort((a, b) => b.score - a.score);
}, [tokens]);

// Memoize callbacks
const handleSort = useCallback((column: string) => {
  setSortColumn(column);
}, []);
```

## Error Handling

### Error Boundary

```typescript
class ErrorBoundary extends React.Component<Props, State> {
  // Catch React errors
  // Display fallback UI
  // Log errors
}
```

### API Error Handling

```typescript
function useTokens() {
  const { data, error, isError } = useQuery({
    queryKey: ['tokens'],
    queryFn: fetchTokens,
    retry: (failureCount, error) => {
      // Don't retry on 404
      if (error.status === 404) return false;
      return failureCount < 3;
    },
  });
  
  if (isError) {
    // Show error toast
    // Provide retry button
  }
}
```

## Testing Strategy

### Unit Tests
- Component rendering
- Hook behavior
- Utility functions

### Integration Tests
- User flows
- API integration
- State management

### E2E Tests (optional)
- Critical user paths
- Cross-browser testing

## Accessibility

### WCAG AA Compliance
- Semantic HTML
- ARIA labels
- Keyboard navigation
- Focus management
- Color contrast ratios
- Screen reader support

### Implementation
```typescript
// Example: Accessible button
<Button
  aria-label="Sort by score"
  onClick={handleSort}
>
  Score
</Button>

// Example: Accessible table
<table role="table" aria-label="Token list">
  <thead>
    <tr role="row">
      <th role="columnheader">Token</th>
    </tr>
  </thead>
</table>
```

## Deployment

### Build Process
```bash
npm run build
# Output: frontend/dist/
```

### Static File Serving
FastAPI serves built files from `frontend/dist/`

### Environment Variables
```env
VITE_API_URL=http://localhost:8000
```

## Migration Strategy

### Phase 1: Setup
- Install dependencies
- Configure Tailwind
- Setup shadcn/ui
- Configure React Query

### Phase 2: Core Components
- Create UI components
- Build layout
- Implement theme system

### Phase 3: Pages
- Migrate Dashboard
- Migrate Token Detail
- Migrate Settings
- Add new features

### Phase 4: Optimization
- Add virtualization
- Implement debouncing
- Code splitting
- Performance testing

### Phase 5: Polish
- Dark theme refinement
- Mobile optimization
- Accessibility audit
- User testing
