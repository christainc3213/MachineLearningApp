import React from 'react';
import NavBar from './NavBar';

type LayoutProps = {
    children: React.ReactNode;
};

const Layout: React.FC<LayoutProps> = ({ children }) => {
    return (
        <div>
            <NavBar />
            <main className="container pt-4">
                {children}
            </main>
        </div>
    );
};


export default Layout;
