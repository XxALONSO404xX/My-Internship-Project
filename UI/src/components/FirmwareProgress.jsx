import { useEffect, useState } from 'react';
import { Box, Progress } from '@chakra-ui/react';

/**
 * Fake firmware update progress bar.
 * Shows linear progress from 0 to 100% over specified duration.
 * Non-linear easing and occasional pauses improve realism.
 */
export default function FirmwareProgress({ duration = 15000, onComplete, progress }) {
  const [percent, setPercent] = useState(0);

  useEffect(() => {
    const start = Date.now();
    let pauseTimeout = null;

    function easeOutCubic(x) {
      return 1 - Math.pow(1 - x, 3);
    }

    // If external progress provided, just follow it
    if (progress !== undefined) {
      setPercent(progress);
      if (progress >= 100) onComplete?.();
      return; // skip fake timer effect
    }

    const id = setInterval(() => {
      const elapsed = Date.now() - start;
      const progressRaw = Math.min(1, elapsed / duration);
      // random 1s pause at ~40-60 %
      if (!pauseTimeout && progressRaw > 0.4 && progressRaw < 0.6 && Math.random() < 0.05) {
        pauseTimeout = setTimeout(() => {
          pauseTimeout = null;
        }, 1000);
      }
      if (pauseTimeout) return; // stay on same percent during pause

      const eased = easeOutCubic(progressRaw);
      setPercent(Math.round(eased * 100));
      if (progressRaw >= 1) {
        clearInterval(id);
        onComplete?.();
      }
    }, 200);

    return () => {
      clearInterval(id);
      if (pauseTimeout) clearTimeout(pauseTimeout);
    };
  }, [duration, onComplete, progress]);

  return (
    <Box w="100%" pt={2}>
      <Progress value={percent} size="sm" colorScheme="purple" borderRadius="sm" />
      <Box fontSize="xs" mt={1} textAlign="right">{percent}%</Box>
    </Box>
  );
}
