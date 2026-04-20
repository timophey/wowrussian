import React from 'react';
import { useTranslation } from 'react-i18next';
import { Box, Container, Typography, Link } from '@mui/material';

function Footer() {
  const { t } = useTranslation();

  return (
    <Box
      data-block="footer"
      component="footer"
      sx={{
        bgcolor: 'background.paper',
        borderTop: 0,
        borderColor: 'divider',
        py: 2,
        mt: 'auto',
      }}
    >
      <Container maxWidth="lg">
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="body2" color="text.secondary">
            © {new Date().getFullYear()} {t('footer.copyright')}
          </Typography>
          <Link href="/legal-info" variant="body2" color="text.secondary">
            {t('footer.legalInfo')}
          </Link>
        </Box>
      </Container>
    </Box>
  );
}

export default Footer;
