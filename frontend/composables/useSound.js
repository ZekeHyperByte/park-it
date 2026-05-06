/**
 * Sound Feedback Composable
 *
 * Web Audio API tones for POS operator feedback.
 * No external audio files needed — all tones generated programmatically.
 */

export function useSound() {
  let audioCtx = null

  function getAudioContext() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume()
    }
    return audioCtx
  }

  function playTone(frequency, duration, type = 'sine', volume = 0.1) {
    try {
      const ctx = getAudioContext()
      const oscillator = ctx.createOscillator()
      const gainNode = ctx.createGain()
      oscillator.connect(gainNode)
      gainNode.connect(ctx.destination)
      oscillator.frequency.value = frequency
      oscillator.type = type
      gainNode.gain.value = volume
      oscillator.start()
      oscillator.stop(ctx.currentTime + duration)
    } catch (err) {
      console.warn('Audio playback failed:', err)
    }
  }

  return {
    vehicleDetected: () => playTone(800, 0.1),
    paymentSuccess: () => {
      playTone(523, 0.15)
      setTimeout(() => playTone(659, 0.15), 150)
    },
    paymentFailed: () => {
      playTone(330, 0.2)
      setTimeout(() => playTone(262, 0.3), 200)
    },
    gateOpen: () => playTone(880, 0.2),
    timeoutAlert: () => {
      playTone(440, 0.1)
      setTimeout(() => playTone(440, 0.1), 200)
      setTimeout(() => playTone(440, 0.1), 400)
    },
  }
}
