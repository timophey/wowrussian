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
          size="small"
          sx={{
            bgcolor: 'background.paper',
            borderRadius: 1,
            '&:hover': {
              bgcolor: 'background.paper',
            },
          }}
        >
          <LanguageIcon fontSize="small" />
          <Box component="span" sx={{ ml: 0.5, fontSize: '0.875rem' }}>
            {i18n.language === 'ru' ? 'EN' : 'RU'}
          </Box>
        </IconButton>
      </Tooltip>
    </Box>
  );
}

export default LanguageSwitcher;
