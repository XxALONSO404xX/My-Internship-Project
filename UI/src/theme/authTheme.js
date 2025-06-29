export const authTheme = {
  colors: {
    primary: {
      50: '#e3f2fd',
      100: '#bbdefb',
      200: '#90caf9',
      300: '#64b5f6',
      400: '#42a5f5',
      500: '#2196f3',
      600: '#1e88e5',
      700: '#1976d2',
      800: '#1565c0',
      900: '#0d47a1',
    },
    secondary: {
      50: '#fce4ec',
      100: '#f8bbd0',
      200: '#f48fb1',
      300: '#f06292',
      400: '#ec407a',
      500: '#e91e63',
      600: '#d81b60',
      700: '#c2185b',
      800: '#ad1457',
      900: '#880e4f',
    },
  },
  components: {
    Button: {
      baseStyle: {
        fontWeight: 'bold',
        borderRadius: 'xl',
        _focus: { boxShadow: 'none' }
      },
      sizes: {
        auth: {
          h: '48px',
          fontSize: 'md',
          px: '32px'
        }
      },
      variants: {
        auth: {
          bg: 'primary.500',
          color: 'white',
          _hover: {
            bg: 'primary.600',
            transform: 'translateY(-2px)'
          },
          _active: {
            bg: 'primary.700'
          }
        }
      }
    },
    Input: {
      variants: {
        auth: {
          field: {
            borderRadius: 'lg',
            borderWidth: '2px',
            _focus: {
              borderColor: 'primary.500',
              boxShadow: '0 0 0 1px primary.500'
            }
          }
        }
      }
    }
  }
}