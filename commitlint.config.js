module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'perf',
        'refactor',
        'docs',
        'test',
        'ci',
        'chore',
        'build',
        'style',
        'revert',
      ],
    ],
    'header-max-length': [2, 'always', 100],
  },
};
