const VueLoaderPlugin = require('vue-loader/lib/plugin')

module.exports = {
    mode: 'development',
    entry: {
        'sequence_labeling': './static/js/annotation/sequence_labeling.js',
        'sequence_labeling_alt': './static/js/annotation/sequence_labeling_alt.js',
        'document_classification': './static/js/annotation/document_classification.js',
        'seq2seq': './static/js/annotation/seq2seq.js',
        'projects': './static/js/projects.js',
        'stats': './static/js/project/stats.js',
        'label': './static/js/project/label.js',
        'labels_admin': './static/js/project/labels_admin.js',
        'labelers': './static/js/project/labelers.js',
        'guideline': './static/js/project/guideline.js',
        'demo_text_classification': './static/js/demo/demo_text_classification.js',
        'demo_named_entity': './static/js/demo/demo_named_entity.js',
        'demo_translation': './static/js/demo/demo_translation.js',
        'upload': './static/js/project/upload.js',
        'navbar': './static/js/navbar.js',
        'settings': './static/js/project/settings.js',
        'dataset': './static/js/project/dataset.js',
        'users': './static/js/users/users.js',
        'user': './static/js/users/user.js',
        'user_info': './static/js/project/user_info.js',
        'ml_model': './static/js/project/ml_model.js'
    },
    output: {
        path: __dirname + '/static/bundle',
        filename: '[name].js'
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: 'vue-loader'
            },
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader'],
            }
        ]
    },
    plugins: [
        new VueLoaderPlugin()
    ],
    resolve: {
        extensions: ['.js', '.vue'],
        alias: {
            vue$: 'vue/dist/vue.esm.js',
        },
    },
}