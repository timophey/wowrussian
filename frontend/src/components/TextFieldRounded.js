import React from 'react';
import TextField from '@mui/material/TextField';
import { styled } from '@mui/material/styles';
import { BorderAll } from '@mui/icons-material';

// Стилизованный TextField с фиксированным outlined, но внешне — rounded
const StyledTextField = styled(TextField)(({ theme }) => ({
  '& .MuiOutlinedInput-root': {
    backgroundColor: '#ffffff',
    borderRadius: '32px',
    // height: '64px',
    '& fieldset': {
      borderColor: theme.palette.grey[300],
      BorderAll: 0,
    },
    '& input': {
      borderRadius: '32px',
      height: '64px',
      boxSizing: 'border-box',
    },
    '&:hover fieldset': {
      borderColor: theme.palette.grey[400],
    },
    '&.Mui-focused fieldset': {
      borderColor: theme.palette.primary.main,
    },
  },
}));

// Компонент-обёртка: принимает variant="rounded" и все остальные пропсы
const TextFieldRounded = (props) => {
  // Если variant явно указан как "rounded", игнорируем его и принудительно ставим "outlined"
  const { variant, ...rest } = props;
  return <StyledTextField variant="outlined" {...rest} />;
};

export default TextFieldRounded;