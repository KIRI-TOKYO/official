const project = {
    server: 'kiri-tokyo:8080',
    character: 'UTF-8',
    eol: '\n'
};

const dir = {
    src: 'asset',
    sass: 'sass',
    css: 'css'
};
const pathRoot = 'docs';
const pathDevRoot = '_dev';
const pathDev = {
    sass: `${pathDevRoot}/${dir.sass}/`,
    mixin: `${pathDevRoot}/${dir.sass}/mixin/addons/`
};
const pathProd = {
    css: `${pathRoot}/${dir.src}/${dir.css}/`,
    js: `${pathRoot}/${dir.src}/${dir.js}/`,
    html: `${pathRoot}/`
};

const gulp = require('gulp');
const plugins = require('gulp-load-plugins')();

const browserSync = require('browser-sync').create();

const autoprefixer = require('autoprefixer');
const cssDeclarationSorter = require('css-declaration-sorter');

gulp.task('compileSass', () => {
    'use strict';

    return gulp.src(`${pathDev.sass}*.scss`)
    .pipe(plugins.dartSass({
        outputStyle: 'expanded'
    }))
    .pipe(plugins.plumber()) // エラー時もファイル監視を続ける
    .pipe(plugins.replace('UTF-8', project.character))
    .pipe(plugins.replace(' \n', '\n'))
    .pipe(plugins.eol(project.eol))
    .pipe(plugins.convertEncoding({
        to: project.character
    }))
    .pipe(plugins.postcss([
        autoprefixer({
            cascade: false
        }),
        cssDeclarationSorter({
            order: 'smacss'
        })
    ]))
    .pipe(gulp.dest(pathProd.css))
    .pipe(browserSync.stream());
});

function bSync() {
    'use strict';

    return browserSync.init({
        proxy: project.server
    });
}

function watchFiles() {
    'use strict';

    return gulp.watch([`${pathDev.sass}**/*.scss`, `${pathDev.root}**/*.html`, `${pathDev.root}/*.html`], gulp.parallel('compileSass'));
}

gulp.task('default', gulp.series(gulp.parallel(bSync, 'compileSass', watchFiles)));
