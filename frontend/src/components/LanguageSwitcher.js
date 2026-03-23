import React from 'react';
import { useTranslation } from 'react-i18next';
import { IconButton, Tooltip, Box } from '@mui/material';
import { Language as LanguageIcon } from '@mui/icons-material';

function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'ru' ? 'en' : 'ru';
    i18n.changeLanguage(newLang);
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 1000,
      }}
    >
      <Tooltip title={i18n.language === 'ru' ? 'Switch to English' : 'Переключить на русский'}>
        <IconButton
          onClick={toggleLanguage}
          color="primary"
          size="small"
          sx={{
            bgcolor: 'background.paper',
            boxShadow: 2,
            '&:hover': {
              bgcolor: 'background.paper',
              opacity: 0.9,
            },
          }}
        >
          <LanguageIcon />
          <Box component="span" sx={{ ml: 1, fontWeight: 'bold' }}>
            {i18n.language === 'ru' ? 'EN' : 'RU'}
          </Box>
        </IconButton>
      </Tooltip>
    </Box>
  );
}

export default LanguageSwitcher;
