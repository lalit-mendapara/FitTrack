import React from 'react';
import Navbar from '../components/layout/Navbar';
import Hero from '../components/home/Hero';
import Testimonials from '../components/home/Testimonials';
import WorkoutMotivation from '../components/home/WorkoutMotivation';
import Footer from '../components/layout/Footer';

const LandingPage = () => {
  const [mousePos, setMousePos] = React.useState({ x: 0, y: 0 });

  React.useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="font-sans text-gray-900 relative overflow-hidden">
      {/* Liquid Cursor Follower */}
      <div 
        className="fixed pointer-events-none z-50 w-96 h-96 bg-gradient-to-r from-indigo-500/30 to-purple-500/30 rounded-full blur-3xl mix-blend-multiply transition-transform duration-700 ease-out will-change-transform"
        style={{
          transform: `translate(${mousePos.x - 192}px, ${mousePos.y - 192}px)`, // Centered (w/2 = 192)
        }}
      />
      
      <Navbar />
      <main className="relative z-10">
        <Hero />
        <Testimonials />
        <WorkoutMotivation />
      </main>
      <Footer />
    </div>
  );
};

export default LandingPage;
