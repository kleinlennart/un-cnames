'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';

export default function Home() {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [cnames, setCnames] = useState<string[]>([]);

    useEffect(() => {
        fetch('/data/cnames.txt')
            .then(res => res.text())
            .then(text => {
                const entries = text.split('\n').filter(line => line.trim()).sort();
                // Remove un.org if it exists in the list to avoid duplication
                const unOrgIndex = entries.indexOf('un.org');
                if (unOrgIndex > -1) {
                    entries.splice(unOrgIndex, 1);
                }
                // Always add un.org at the beginning
                setCnames(['www.un.org', ...entries]);
            })
            .catch(err => console.error('Failed to load cnames:', err));
    }, []);

    useEffect(() => {
        if (cnames.length === 0) return;

        const interval = setInterval(() => {
            setCurrentIndex(prev => (prev + 1) % cnames.length);
        }, 2000);

        return () => clearInterval(interval);
    }, [cnames]);

    return (
        <div className="flex min-h-screen items-center justify-center px-8">
            <div className="absolute top-8 left-8">
                <Image
                    src="/images/UN_Logo_Stacked_Colour_English.svg"
                    alt="UN Logo"
                    width={100}
                    height={100}
                    className="w-35 h-auto"
                />
            </div>
            <div className="text-center">
                <p className="text-6xl font-bold">{cnames[currentIndex]}</p>
            </div>
        </div>
    );
}
