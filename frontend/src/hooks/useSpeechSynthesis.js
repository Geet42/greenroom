import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

export function useSpeechSynthesis() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioRef = useRef(null);
  const audioUrlRef = useRef(null);
  // True only for a full stop() (discard audio for good). Kept distinct from
  // "paused" — reusing one flag for both meant muting mid-fetch discarded
  // the in-flight audio outright, so unmuting had nothing left to resume.
  const cancelledRef = useRef(false);
  const pausedRef = useRef(false);
  // Bumped on every speak()/stop() call. A speak() call only ever acts on
  // its own generation — if a newer speak() (or a stop()) starts while an
  // older one's TTS fetch is still in flight, the older one sees its token
  // no longer matches and discards itself instead of also playing, which is
  // exactly how "current and previous question both spoken" happened: two
  // speak() calls' fetches could both resolve and both call audio.play()
  // with nothing to stop the first from finishing what it started.
  const generationRef = useRef(0);
  // Once the owning component unmounts, no further speak() call may start
  // audio — otherwise a request that was already in flight (e.g. the
  // interviewer's reply arriving after the user navigated away) resets
  // cancelledRef and plays audio nobody can stop anymore.
  const isMountedRef = useRef(true);
  useEffect(() => () => { isMountedRef.current = false; }, []);

  const revokeAudioUrl = () => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  };

  // Immediately halts whatever's currently playing (Audio element or the
  // browser speechSynthesis fallback) — called synchronously at the start of
  // every speak()/stop(), before any async work, so there is never a window
  // where two audio sources are both live.
  const killCurrentPlayback = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    revokeAudioUrl();
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  };

  const speak = useCallback(async (text) => {
    if (!text || !isMountedRef.current) return;
    const myGeneration = ++generationRef.current;
    killCurrentPlayback();
    cancelledRef.current = false;
    setIsSpeaking(true);

    const isCurrent = () => generationRef.current === myGeneration && isMountedRef.current;

    try {
      const url = await api.speak(text);
      // A newer speak(), or stop(), ran while this fetch was in flight —
      // discard instead of starting playback over whatever's now current.
      if (!isCurrent() || cancelledRef.current) {
        URL.revokeObjectURL(url);
        return;
      }
      audioUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { if (isCurrent()) setIsSpeaking(false); revokeAudioUrl(); };
      audio.onerror = () => { revokeAudioUrl(); if (isCurrent() && !cancelledRef.current) fallbackToBrowser(text); };
      if (pausedRef.current) {
        // Muted while this fetch was still in flight — keep the audio ready
        // to play from the start instead of dropping it, so unmuting has
        // something to resume.
        setIsSpeaking(false);
        return;
      }
      await audio.play();
    } catch {
      if (isCurrent() && !cancelledRef.current && !pausedRef.current) fallbackToBrowser(text);
    }

    function fallbackToBrowser(value) {
      if (!("speechSynthesis" in window)) {
        setIsSpeaking(false);
        return;
      }
      const utterance = new SpeechSynthesisUtterance(value);
      utterance.rate = 1;
      utterance.onend = () => { if (isCurrent()) setIsSpeaking(false); };
      window.speechSynthesis.speak(utterance);
    }
  }, []);

  const stop = useCallback(() => {
    generationRef.current++;
    cancelledRef.current = true;
    pausedRef.current = false;
    killCurrentPlayback();
    setIsSpeaking(false);
  }, []);

  // pause mid-sentence (keeps position so resume() can continue from same spot)
  const pause = useCallback(() => {
    pausedRef.current = true;
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
    }
    if ("speechSynthesis" in window) {
      window.speechSynthesis.pause();
    }
    setIsSpeaking(false);
  }, []);

  // resume from where pause() stopped
  const resume = useCallback(() => {
    pausedRef.current = false;
    if (audioRef.current && !audioRef.current.ended) {
      audioRef.current.play();
      setIsSpeaking(true);
    } else if ("speechSynthesis" in window && window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      setIsSpeaking(true);
    }
  }, []);

  return { isSpeaking, speak, stop, pause, resume };
}
