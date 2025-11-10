import type { NextConfig } from 'next'

// Set to your repository name for GitHub Pages, or '' for custom domain
// When using a custom domain (CNAME), set BASE_PATH to '' in your environment
const basePath = process.env.NODE_ENV === 'production' ? (process.env.BASE_PATH || '') : ''

// NOTE: use basePath variable for Image src 
// https://nextjs.org/docs/app/api-reference/config/next-config-js/basePath#images

const nextConfig: NextConfig = {
    output: 'export',
    trailingSlash: true,
    basePath: basePath,
    assetPrefix: basePath,
    images: {
        unoptimized: true
    },
    env: {
        NEXT_PUBLIC_BASE_PATH: basePath,
    },
}

export default nextConfig