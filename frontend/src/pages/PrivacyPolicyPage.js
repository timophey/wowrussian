import React from 'react';
import { useTranslation } from 'react-i18next';
import { Container, Typography, Box, Paper, Link, List, ListItem, ListItemText } from '@mui/material';

function PrivacyPolicyPage() {
  const { t } = useTranslation();

  return (
    <Container data-block="privacy-policy-container" maxWidth="md" sx={{ mt: 8, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          {t('privacy.title')}
        </Typography>
        
        <Typography variant="body2" color="text.secondary" align="center" paragraph>
          {t('privacy.lastUpdated')}: {new Date().toLocaleDateString('ru-RU')}
        </Typography>

        <Box sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>
            1. {t('privacy.general.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.general.content')}
          </Typography>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            2. {t('privacy.operator.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.operator.content')}
          </Typography>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            3. {t('privacy.collectedData.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.collectedData.content')}
          </Typography>
          <List>
            <ListItem>
              <ListItemText primary={t('privacy.collectedData.items.email')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.collectedData.items.password')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.collectedData.items.ipAddress')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.collectedData.items.userAgent')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.collectedData.items.sessionData')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.collectedData.items.analysisData')} />
            </ListItem>
          </List>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            4. {t('privacy.purposes.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.purposes.content')}
          </Typography>
          <List>
            <ListItem>
              <ListItemText primary={t('privacy.purposes.items.authentication')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.purposes.items.serviceProvision')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.purposes.items.improvement')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.purposes.items.security')} />
            </ListItem>
          </List>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            5. {t('privacy.legalBasis.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.legalBasis.content')}
          </Typography>
          <List>
            <ListItem>
              <ListItemText primary={t('privacy.legalBasis.items.consent')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.legalBasis.items.contract')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.legalBasis.items.legitimateInterest')} />
            </ListItem>
          </List>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            6. {t('privacy.storage.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.storage.content')}
          </Typography>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            7. {t('privacy.rights.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.rights.content')}
          </Typography>
          <List>
            <ListItem>
              <ListItemText primary={t('privacy.rights.items.access')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.rights.items.correction')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.rights.items.deletion')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.rights.items.restriction')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.rights.items.portability')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.rights.items.objection')} />
            </ListItem>
            <ListItem>
              <ListItemText primary={t('privacy.rights.items.complaint')} />
            </ListItem>
          </List>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            8. {t('privacy.cookies.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.cookies.content')}
          </Typography>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            9. {t('privacy.thirdParty.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.thirdParty.content')}
          </Typography>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            10. {t('privacy.security.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.security.content')}
          </Typography>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            11. {t('privacy.changes.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.changes.content')}
          </Typography>

          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            12. {t('privacy.contact.title')}
          </Typography>
          <Typography variant="body1" paragraph>
            {t('privacy.contact.content')}
          </Typography>
        </Box>

        <Box sx={{ mt: 4, pt: 3, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="body2" color="text.secondary" align="center">
            {t('privacy.contact.email')}: <Link href="mailto:privacy@wowrussian.ru">privacy@wowrussian.ru</Link>
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}

export default PrivacyPolicyPage;
