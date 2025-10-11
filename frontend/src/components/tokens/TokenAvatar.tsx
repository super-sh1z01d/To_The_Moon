import { useState } from 'react'
import { cn } from '@/lib/utils'

interface TokenAvatarProps {
  imageUrl?: string | null
  fallback: string
  alt?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const SIZE_CLASSES: Record<TokenAvatarProps['size'], string> = {
  sm: 'h-8 w-8 text-sm',
  md: 'h-10 w-10 text-base',
  lg: 'h-12 w-12 text-lg',
}

export function TokenAvatar({
  imageUrl,
  fallback,
  alt,
  size = 'sm',
  className,
}: TokenAvatarProps) {
  const [errored, setErrored] = useState(false)
  const displayImage = typeof imageUrl === 'string' && imageUrl.length > 0 && !errored
  const trimmedFallback = fallback?.trim() ?? ''
  const fallbackChar = trimmedFallback ? Array.from(trimmedFallback)[0] ?? '?' : '?'

  return (
    <div
      className={cn(
        'flex-shrink-0 flex items-center justify-center overflow-hidden rounded-sm border border-muted bg-background text-muted-foreground p-0.5',
        SIZE_CLASSES[size],
        className
      )}
    >
      {displayImage ? (
        <img
          src={imageUrl}
          alt={alt ?? fallback}
          className="h-full w-full object-cover"
          loading="lazy"
          onError={() => setErrored(true)}
        />
      ) : (
        <span className="select-none">{fallbackChar}</span>
      )}
    </div>
  )
}
