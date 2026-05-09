/**
 * useKeyboard — centralized keyboard shortcut management.
 * Registers/unregisters on mount/unmount.
 */

import { onMounted, onUnmounted } from 'vue'

export function useKeyboard(handlers) {
  function onKeydown(e) {
    // Don't trigger shortcuts when typing in inputs
    const tag = e.target.tagName
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable

    for (const handler of handlers) {
      const matches = handler.keys.every((key) => {
        if (key === 'ctrl') return e.ctrlKey || e.metaKey
        if (key === 'shift') return e.shiftKey
        if (key === 'alt') return e.altKey
        return e.key === key
      })

      if (matches) {
        // Skip single-key shortcuts when typing in inputs
        if (isInput && handler.keys.length === 1 && !['Escape', 'F1', 'F2', 'F3', 'F4'].includes(handler.keys[0])) {
          continue
        }
        e.preventDefault()
        handler.action()
        return
      }
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', onKeydown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', onKeydown)
  })
}
