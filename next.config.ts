import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
    output: 'export',
    basePath: '', // Explicitly set to empty string for root deployment
    assetPrefix: '', // Explicitly set to empty string for root deployment
    trailingSlash: true,
    images: {
        unoptimized: true
    },
}

export default nextConfig