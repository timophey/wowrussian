import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Typography, Button, Link, Container } from '@mui/material';

function CookieConsentBanner() {
  const { t } = useTranslation();
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    const consentGiven = localStorage.getItem('cookie_consent');
    if (!consentGiven) {
      setShowBanner(true);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem('cookie_consent', 'true');
    setShowBanner(false);
  };

  const handleDecline = () => {
    localStorage.setItem('cookie_consent', 'false');
    setShowBanner(false);
  };

  if (!showBanner) {
    return null;
  }

  return (
    <Box
      data-block="cookie-consent"
      sx={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        bgcolor: 'background.paper',
        boxShadow: '0 -2px 10px rgba(0,0,0,0.1)',
        py: 2,
        zIndex: 1100,
        borderTop: 1,
        borderColor: 'divider',
      }}
    >
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, alignItems: { xs: 'flex-start', sm: 'center' }, justifyContent: 'space-between', gap: 2 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="body1" sx={{ mb: 1 }}>
              {t('cookieConsent.message')}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              <Link href="/privacy-policy" target="_blank">
                {t('cookieConsent.learnMore')}
              </Link>
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
            <Button
              variant="outlined"
              size="small"
              onClick={handleDecline}
            >
              {t('cookieConsent.decline')}
            </Button>
            <Button
              variant="contained"
              size="small"
              onClick={handleAccept}
            >
              {t('cookieConsent.accept')}
            </Button>
          </Box>
        </Box>
      </Container>
    </Box>
  );
}

export default CookieConsentBanner;
