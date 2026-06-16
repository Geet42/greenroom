import { useCallback, useEffect, useRef, useState } from "react";

const SpeechRecognitionImpl =
  typeof window !== "undefined"
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

export function useSpeechRecognition() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [isSupported, setIsSupported] = useState(!!SpeechRecognitionImpl);
  const recognitionRef = useRef(null);

  useEffect(() => {
    if (!SpeechRecognitionImpl) {
      setIsSupported(false);
      return;
    }

    const recognition = new SpeechRecognitionImpl();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalText += result[0].transcript;
        } else {
          interimText += result[0].transcript;
        }
      }
      if (finalText) {
        setTranscript((prev) => (prev ? `${prev} ${finalText}`.trim() : finalText.trim()));
      }
      setInterimTranscript(interimText);
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterimTranscript("");
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.stop();
    };
  }, []);

  const start = useCallback(() => {
    if (!recognitionRef.current) return;
    setTranscript("");
    setInterimTranscript("");
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch {
      // already started
    }
  }, []);

  const stop = useCallback(() => {
    if (!recognitionRef.current) return;
    recognitionRef.current.stop();
    setIsListening(false);
  }, []);

  const reset = useCallback(() => {
    setTranscript("");
    setInterimTranscript("");
  }, []);

  return { isSupported, isListening, transcript, interimTranscript, start, stop, reset };
}
