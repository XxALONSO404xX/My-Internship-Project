import { IconButton, useColorMode } from '@chakra-ui/react';
import { MoonIcon, SunIcon } from '@chakra-ui/icons';

/**
 * Theme toggle button component for switching between light and dark modes
 */
export default function ThemeToggle() {
  const { colorMode, toggleColorMode } = useColorMode();
  
  return (
    <IconButton
      aria-label="Toggle theme"
      icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
      onClick={toggleColorMode}
      variant="ghost"
      position="fixed"
      bottom="4"
      right="4"
      zIndex="docked"
    />
  );
}
