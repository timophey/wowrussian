import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#6E63E5',
    },
    secondary: {
      main: '#dc004e',
    },
    text: {
        primary: '#2A2948',
    }
  },
  typography: {
    fontSize: 14,
    fontFamily: '"Manrope", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
    },        
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '160px', // все кнопки будут с круглыми углами
          padding: '10px 22px',
        },
      },
    },
    MuiPaper: {
        styleOverrides: {
            root: {
                boxShadow: 'none',
            }
        }
    },
    MuiTabs: {
        styleOverrides: {
            scroller: {
                display: 'flex',
            },
            flexContainer: {
                justifyContent: 'center',
                margin: '0 auto',
                backgroundColor: '#F8F8FC',
                borderRadius: '100px',
                padding: '8px',
                gap: '4px',
            },
            indicator: {
                height: 0,
            }
        },
    },
    MuiTab: {
        styleOverrides: {
            root: {
                padding: '10px 20px 10px 12px',
                borderRadius: '22px',
                minHeight: '44px',
            }
        }
    },
    MuiFormControl: {
        styleOverrides: {
            root: {

            }
        }
    },
    InputBase: {
        styleOverrides: {
            inputAdornedStart: {
                backgroundColor: '#FFF',
                backgroundColor: 'red',
                borderRadius: '100px',
            }
        }
    },
    MuiFormHelperText: {
        styleOverrides: {
            root: {
                textAlign: 'center',
                fontSize: '18px',
                marginTop: '24px',
            }
        }
    },
    MuiDialog: {
        styleOverrides: {
            paper: {
                padding: '80px 96px',
            }
        }
    }
  },
});

export default theme;