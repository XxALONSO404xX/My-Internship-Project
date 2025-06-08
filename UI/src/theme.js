// Chakra UI theme configuration
import { extendTheme } from '@chakra-ui/react';
import { mode } from '@chakra-ui/theme-tools';
import { authTheme } from './theme/authTheme';

const config = {
  initialColorMode: 'light',
  useSystemColorMode: true, // respect system theme and persisted user preference
};

const colors = {
  brand: {
    50: '#e3f9e5',
    100: '#c1eac5',
    200: '#a3d9a5',
    300: '#7bc47f',
    400: '#57ae5b',
    500: '#3f9142',
    600: '#2f8132',
    700: '#207227',
    800: '#0e5814',
    900: '#05400a',
  },
};

const styles = {
  global: (props) => ({
    // Smooth theme transition
    'html, body': {
      transition: 'background-color 0.3s ease, color 0.3s ease',
    },
    '*, *::before, *::after': {
      transition: 'background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease',
    },
    body: {
      bg: mode('gray.50', 'gray.800')(props),
      color: mode('gray.800', 'whiteAlpha.900')(props),
    },
  }),
};

// Helper to create Box-like "card" variant (glass style)
const glassCardBase = {
  bg: 'whiteAlpha.900',
  borderRadius: 'xl',
  borderWidth: '1px',
  borderColor: 'gray.200',
  _dark: {
    bg: 'gray.800',
    borderColor: 'gray.700',
  },
  boxShadow: 'xl',
  backdropFilter: 'blur(10px)',
};

const theme = extendTheme({
  config,
  colors: {
    ...colors,
    ...authTheme.colors,
  },
  styles,
  components: {
    ...authTheme.components,
    // Box variant for reusable "card" appearance
    Box: {
      variants: {
        card: glassCardBase,
      },
    },
    Button: {
      ...authTheme.components?.Button,
      defaultProps: {
        colorScheme: 'primary',
      },
    },
  },
});
export default theme;
