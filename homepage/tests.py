from django.test import SimpleTestCase, override_settings


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class HomepageLayoutTests(SimpleTestCase):
    def test_home_prioritises_orac_and_groups_old_projects(self):
        response = self.client.get('/')
        self.assertContains(response, 'ORAC Leaderboards++')
        self.assertContains(response, '/archive/')
        self.assertContains(response, 'href="/67/"')
        self.assertNotContains(response, '/vce/')
        self.assertNotContains(response, '/67vce/')

    def test_archive_keeps_existing_project_links(self):
        response = self.client.get('/archive/')
        for path in ('/67/', '/67/hall-of-fame/', '/vce/', '/67vce/'):
            self.assertContains(response, path)
