import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Container, Typography, Box, Paper, Divider, CircularProgress, Alert } from '@mui/material';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

function LegalInfoPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [legalInfo, setLegalInfo] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    axios.get(`${API_BASE_URL}/auth/legal-info`)
      .then(response => {
        setLegalInfo(response.data);
        setLoading(false);
      })
      .catch(() => {
        setError(t('errors.failedToLoad'));
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 8, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ mt: 8 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  const { operator } = legalInfo || {};
  const hasOperatorInfo = operator && Object.keys(operator).length > 0;

  return (
    <Container data-block="legal-info-container" maxWidth="md" sx={{ mt: 8, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          {t('legalInfo.title')}
        </Typography>

        {/* Operator Information */}
        {hasOperatorInfo && (
          <Box sx={{ mt: 4 }}>
            <Typography variant="h5" gutterBottom>
              {t('legalInfo.operator.title')}
            </Typography>
            <Box sx={{ pl: 2 }}>
              {operator.name && (
                <Typography variant="body1" paragraph>
                  <strong>{t('legalInfo.operator.name')}:</strong> {operator.name}
                </Typography>
              )}
              {operator.address && (
                <Typography variant="body1" paragraph>
                  <strong>{t('legalInfo.operator.address')}:</strong> {operator.address}
                </Typography>
              )}
              {operator.inn && (
                <Typography variant="body1" paragraph>
                  <strong>{t('legalInfo.operator.inn')}:</strong> {operator.inn}
                </Typography>
              )}
              {operator.ogrn && (
                <Typography variant="body1" paragraph>
                  <strong>{t('legalInfo.operator.ogrn')}:</strong> {operator.ogrn}
                </Typography>
              )}
              {operator.email && (
                <Typography variant="body1" paragraph>
                  <strong>{t('legalInfo.operator.email')}:</strong>{' '}
                  <a href={`mailto:${operator.email}`}>{operator.email}</a>
                </Typography>
              )}
            </Box>
          </Box>
        )}

        <Divider sx={{ my: 4 }} />

        {/* Disclaimer Section */}
        <Box sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>
            {t('legalInfo.disclaimer.title')}
          </Typography>

          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            {t('legalInfo.disclaimer.asIs.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('legalInfo.disclaimer.asIs.content')}
          </Typography>

          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            {t('legalInfo.disclaimer.notLegalAdvice.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('legalInfo.disclaimer.notLegalAdvice.content')}
          </Typography>

          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            {t('legalInfo.disclaimer.limitation.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('legalInfo.disclaimer.limitation.content')}
          </Typography>

          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            {t('legalInfo.disclaimer.dataPurpose.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('legalInfo.disclaimer.dataPurpose.content')}
          </Typography>

          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            {t('legalInfo.disclaimer.cookies.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('legalInfo.disclaimer.cookies.content')}
          </Typography>
        </Box>

        <Divider sx={{ my: 4 }} />

        {/* Law Reference */}
        <Box sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>
            {t('legalInfo.lawReference.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('legalInfo.lawReference.content')}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {legalInfo?.law_reference}
          </Typography>
        </Box>

        <Box sx={{ mt: 4, pt: 3, borderTop: 1, borderColor: 'divider', textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            {t('legalInfo.privacyPolicyLink')}: <a href="/privacy-policy">{t('legalInfo.privacyPolicy')}</a>
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}

export default LegalInfoPage;
