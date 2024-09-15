import { themes as prismThemes } from 'prism-react-renderer';
import type { Config } from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

require('dotenv').config();

// Define variables for siteUrl and baseUrl so we can use them
const siteUrl = process.env.SITE_URL || 'https://mahendrapaipuri.gitlab.io';
const baseUrl = '/gitlab-activity';
const repoUrl = 'https://gitlab.com/mahendrapaipuri/gitlab-activity';

const config: Config = {
  title: 'gitlab-activity',
  tagline: 'An automatic changelog generator for GitLab projects',
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: siteUrl,
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: baseUrl,

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  // organizationName: 'mahendrapaipuri', // Usually your GitHub org/user name.
  // projectName: 'gitlab-activity', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl: `${repoUrl}/-/tree/main/docs/website`,
        },
        blog: {
          showReadingTime: true,
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl: `${repoUrl}/-/tree/main/docs/website`,
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    // image: 'img/gitlab-card.jpg',
    docs: {
      sidebar: {
        // Make sidebar hideable
        hideable: true,
        // Collapse all sibling categories when expanding one category
        autoCollapseCategories: true,
      },
    },
    navbar: {
      title: 'GitLab Activity Documentation',
      logo: {
        alt: 'GitLab Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'doc',
          docId: 'intro',
          position: 'left',
          label: 'Getting Started',
        },
        {
          href: `${siteUrl}${baseUrl}/api/`,
          label: 'API',
          position: 'left',
        },
        { to: '/blog', label: 'Blog', position: 'left' },
        {
          href: `${repoUrl}`,
          label: 'GitLab',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Repository',
          items: [
            {
              label: 'Issues',
              href: `${repoUrl}/-/issues`,
            },
            {
              label: 'Merge Requests',
              href: `${repoUrl}/-/merge_requests`,
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'Blog',
              to: '/blog',
            },
            {
              label: 'GitLab',
              href: `${repoUrl}`,
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()}. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
