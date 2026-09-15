import { useCallback, useEffect, useRef } from 'react'

/**
 * Gentle "fade + rise as it enters the viewport" reveal, used for Home's
 * below-the-fold sections (Phase 8A: visual refinement). Dependency-free
 * (IntersectionObserver, no scroll library) and additive: consumers apply
 * a `reveal` CSS class (opacity/transform + transition) to each element and
 * this hook adds a second class once the element has actually scrolled
 * into view, then stops observing it — a one-shot reveal, not a repeating
 * scroll effect. Under prefers-reduced-motion, every element is marked
 * visible immediately and no observer is created at all.
 *
 * Returns a ref-callback factory (`setRef(i)`), not the underlying mutable
 * array itself, so consumers never assign into a value a hook returned —
 * the array stays entirely encapsulated in this module.
 */
export function useRevealRefs<T extends HTMLElement>(count: number, visibleClassName: string) {
  const elements = useRef<(T | null)[]>(Array.from({ length: count }, () => null))

  useEffect(() => {
    const targets = elements.current.filter((el): el is T => el !== null)
    if (targets.length === 0) return

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      for (const el of targets) el.classList.add(visibleClassName)
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add(visibleClassName)
            observer.unobserve(entry.target)
          }
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' },
    )
    for (const el of targets) observer.observe(el)
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [count, visibleClassName])

  return useCallback(
    (index: number) => (el: T | null) => {
      elements.current[index] = el
    },
    [],
  )
}
