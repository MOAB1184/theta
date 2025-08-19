
import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const FaqItem: React.FC<{ q: string, children: React.ReactNode }> = ({ q, children }) => {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="border-b border-border-color">
      <button onClick={() => setIsOpen(!isOpen)} className="flex justify-between items-center w-full py-5 text-left">
        <span className="text-lg font-medium text-text-primary">{q}</span>
        <svg className={`w-5 h-5 text-text-secondary transform transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && <div className="pb-5 pr-10 text-text-secondary prose prose-invert prose-p:text-text-secondary">{children}</div>}
    </div>
  );
};


// --- DETAILED MOCKUP COMPONENTS ---

const DashboardMockup: React.FC<{ className?: string }> = ({ className }) => (
    <div className={`bg-secondary p-2 sm:p-3 rounded-xl border border-border-color/50 shadow-2xl shadow-accent/10 ${className}`}>
        <div className="bg-primary w-full h-full rounded-lg p-4 flex gap-4">
            <div className="w-1/4 bg-secondary/50 rounded-md p-2 space-y-2">
                <div className="h-4 bg-border-color rounded w-5/6"></div>
                <div className="h-4 bg-accent/30 rounded w-full"></div>
                <div className="h-4 bg-border-color rounded w-4/6 opacity-70"></div>
                <div className="h-4 bg-border-color rounded w-4/6 opacity-70"></div>
            </div>
            <div className="w-3/4 space-y-3">
                <div className="h-6 bg-border-color rounded w-3/4"></div>
                <div className="h-10 bg-secondary/50 border border-border-color rounded-md flex items-center p-2 justify-between">
                    <div className="h-4 bg-border-color rounded w-1/2"></div>
                    <div className="h-6 bg-accent/30 rounded-md w-1/4"></div>
                </div>
                <div className="h-10 bg-secondary/50 border border-border-color rounded-md flex items-center p-2 justify-between opacity-80">
                    <div className="h-4 bg-border-color rounded w-3/5"></div>
                    <div className="h-6 bg-border-color rounded-md w-1/4"></div>
                </div>
                 <div className="h-10 bg-green-900/20 border border-green-500/20 rounded-md flex items-center p-2 justify-between">
                    <div className="h-4 bg-green-500/30 rounded w-1/2 line-through"></div>
                    <div className="h-5 w-5 bg-green-500/50 rounded-full"></div>
                </div>
            </div>
        </div>
    </div>
)

const HowItWorksMockup: React.FC<{ children: React.ReactNode, className?: string }> = ({ children, className }) => (
    <div className={`h-40 w-full bg-primary rounded-lg border border-border-color flex items-center justify-center p-2 mb-4 overflow-hidden shadow-inner shadow-black/20 ${className}`}>
        {children}
    </div>
);

const FeaturesSection = () => {
    const Feature = ({ icon, title, children, image, imageSide = 'right' }: { icon: React.ReactNode, title: string, children: React.ReactNode, image: React.ReactNode, imageSide?: 'left' | 'right' }) => (
        <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className={imageSide === 'left' ? 'md:order-2' : 'md:order-1'}>
                {image}
            </div>
            <div className={imageSide === 'left' ? 'md:order-1' : 'md:order-2'}>
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-secondary text-accent mb-4 border border-border-color">
                    {icon}
                </div>
                <h3 className="text-3xl font-bold text-text-primary mb-3">{title}</h3>
                <p className="text-lg text-text-secondary">{children}</p>
            </div>
        </div>
    );

    return (
        <section id="features" className="py-28">
            <div className="max-w-6xl mx-auto px-4 text-center md:text-left">
                <div className="text-center mb-20">
                    <h2 className="text-4xl font-bold text-text-primary">Everything You Need, All in One Place</h2>
                    <p className="text-lg text-text-secondary mt-3">A powerful toolkit for both scouts and leaders.</p>
                </div>
                <div className="space-y-24">
                    <Feature
                        title="Visual Progress Tracking"
                        icon={<svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 012-2h2a2 2 0 012 2v6m-6 0h6M9 19H5a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v10a2 2 0 01-2 2h-4" /></svg>}
                        image={<DashboardMockup />}
                        imageSide="right"
                    >
                        Never lose track of your journey. Our intuitive dashboard gives scouts a clear view of their completed requirements and what's next on their path to Eagle.
                    </Feature>
                    <Feature
                        title="Prepare with an AI Guide"
                        icon={<svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 16.663c.52-1.261 1.23-2.422 2.064-3.525m-.012 6.05c-.694.19-1.392.358-2.097.483m2.109-6.533c.832-1.102 1.54-2.263 2.064-3.525M12 21a9 9 0 100-18 9 9 0 000 18z" /></svg>}
                        image={<DashboardMockup className="transform -rotate-2" />}
                        imageSide="left"
                    >
                        Go beyond memorization. Engage with our AI Scoutmaster to test your knowledge through interactive conversations, ensuring you're truly prepared for your sign-off.
                    </Feature>
                    <Feature
                        title="Streamlined Sign-Offs for Leaders"
                        icon={<svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
                        image={<DashboardMockup />}
                        imageSide="right"
                    >
                        Reduce administrative overhead. Scoutmasters get a centralized dashboard to manage sign-off requests, view scout progress, and configure troop settings with ease.
                    </Feature>
                </div>
            </div>
        </section>
    );
};

// --- END MOCKUP COMPONENTS ---

const HeroSection = () => (
    <section className="text-center md:text-left pt-20 pb-28">
        <div className="max-w-7xl mx-auto px-4 grid md:grid-cols-2 gap-12 items-center">
            <div>
                <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 mb-6 tracking-tight">
                    The Modern Toolkit for Scout Advancement
                </h1>
                <p className="text-lg text-text-secondary max-w-3xl mx-auto leading-relaxed">
                    An all-in-one platform for scouts and leaders to track progress, master requirements, and streamline sign-offs.
                </p>
                <div className="flex justify-center md:justify-start">
                    <Link to="/signup" className="bg-accent text-white font-semibold py-3 px-8 rounded-lg hover:bg-accent-hover transition duration-300 text-lg shadow-[0_0_20px_theme(colors.accent/0.5)]">
                        Get Started for Free
                    </Link>
                </div>
            </div>
            <div className="hidden md:block">
                <DashboardMockup className="transform rotate-3" />
            </div>
        </div>
    </section>
);

const TrustedBySection = () => {
    const EmblemIcon = () => (
      <svg className="w-10 h-10 text-text-secondary/60 group-hover:text-text-secondary/80 transition-colors" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M54.5 13.2L32 4 9.5 13.2v37.6L32 60l22.5-9.2V13.2z" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M44 24.4L32 20l-12 4.4v15.2L32 44l12-4.4V24.4z" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
    return (
        <section className="py-12">
            <div className="max-w-5xl mx-auto px-4">
                <p className="text-center text-text-secondary font-semibold tracking-widest text-sm">TRUSTED BY TROOPS AND COUNCILS</p>
                <div className="mt-8 flex justify-center items-center gap-x-12 sm:gap-x-16 opacity-60">
                    <div className="flex items-center gap-3 group cursor-pointer">
                        <EmblemIcon />
                        <span className="font-bold text-lg text-text-secondary/70 group-hover:text-text-secondary/90 transition-colors">Oakwood Council</span>
                    </div>
                    <div className="hidden sm:flex items-center gap-3 group cursor-pointer">
                         <EmblemIcon />
                        <span className="font-bold text-lg text-text-secondary/70 group-hover:text-text-secondary/90 transition-colors">Troop 185</span>
                    </div>
                     <div className="hidden sm:flex items-center gap-3 group cursor-pointer">
                         <EmblemIcon />
                        <span className="font-bold text-lg text-text-secondary/70 group-hover:text-text-secondary/90 transition-colors">Pine Ridge District</span>
                    </div>
                </div>
            </div>
        </section>
    );
}

const HowItWorksSection = () => (
    <section id="how-it-works" className="py-20 bg-secondary/30">
        <div className="max-w-6xl mx-auto px-4">
            <div className="text-center">
                <h2 className="text-4xl font-bold text-text-primary">Path to Advancement, Simplified</h2>
                <p className="text-lg text-text-secondary mt-3">A clear, four-step process for efficient and effective skill development.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-12 text-center mt-16">
                <div className="flex flex-col items-center">
                    <HowItWorksMockup>
                        <div className="w-5/6 bg-secondary p-3 rounded-md border border-border-color space-y-2">
                           <div className="h-3 w-1/2 bg-border-color rounded"></div>
                           <div className="h-2 w-full bg-border-color/70 rounded"></div>
                           <div className="h-2 w-5/6 bg-border-color/70 rounded"></div>
                        </div>
                    </HowItWorksMockup>
                    <h3 className="font-semibold text-xl mb-2 text-text-primary">1. Learn</h3>
                    <p className="text-text-secondary">Access structured lessons and content for any requirement.</p>
                </div>
                <div className="flex flex-col items-center">
                    <HowItWorksMockup>
                         <div className="w-5/6 h-full flex flex-col justify-end gap-2 p-2">
                            <div className="w-2/3 bg-secondary p-2 rounded-lg self-start h-8"></div>
                            <div className="w-3/4 bg-accent p-2 rounded-lg self-end h-8"></div>
                         </div>
                    </HowItWorksMockup>
                    <h3 className="font-semibold text-xl mb-2 text-text-primary">2. Test</h3>
                    <p className="text-text-secondary">Pass our smart chatbot quiz to ensure you're prepared.</p>
                </div>
                <div className="flex flex-col items-center">
                    <HowItWorksMockup>
                        <div className="w-5/6 h-12 bg-green-500/20 rounded-md border border-green-500/30 flex items-center justify-center text-sm font-semibold text-green-400">
                            Request Sign-off
                        </div>
                    </HowItWorksMockup>
                    <h3 className="font-semibold text-xl mb-2 text-text-primary">3. Request</h3>
                    <p className="text-text-secondary">Digitally notify a leader that you're ready for review.</p>
                </div>
                <div className="flex flex-col items-center">
                    <HowItWorksMockup>
                        <div className="w-5/6 bg-secondary p-2 rounded-md border border-border-color space-y-2">
                           <div className="flex justify-between items-center">
                                <div className="h-3 w-1/3 bg-border-color rounded"></div>
                                <div className="h-5 w-1/4 bg-accent/40 rounded-md"></div>
                           </div>
                           <div className="h-2 w-2/3 bg-border-color/70 rounded"></div>
                        </div>
                    </HowItWorksMockup>
                    <h3 className="font-semibold text-xl mb-2 text-text-primary">4. Validate</h3>
                    <p className="text-text-secondary">Meet your leader to demonstrate your skill for the final sign-off.</p>
                </div>
            </div>
        </div>
    </section>
);


const FaqSection = () => (
    <section id="faq" className="py-20">
        <div className="max-w-3xl mx-auto px-4">
            <h2 className="text-center text-4xl font-bold text-text-primary mb-12">Frequently Asked Questions</h2>
            <FaqItem q="Is this a replacement for the Scout Handbook?">
                <p>Not at all. Scout Accelerator is a digital companion to the official handbook. It's designed to help scouts learn the material, track their progress, and streamline the administrative parts of advancement, but the handbook remains the primary reference.</p>
            </FaqItem>
            <FaqItem q="How much does Scout Accelerator cost?">
                <p>Scout Accelerator is completely free to use. Our goal is to provide a powerful, accessible tool to support the scouting community without any financial burden.</p>
            </FaqItem>
            <FaqItem q="Is the sign-off process completely digital?">
                <p>No. Our platform makes the process more efficient, but does not replace tradition. Scouts use our platform to track their progress and study lesson content for each requirement. When ready, they send a digital request to a leader. The final step is still a face-to-face meeting where the scout demonstrates their skill to the leader for the official sign-off. This ensures the integrity of the advancement process.</p>
            </FaqItem>
            <FaqItem q="Is my troop's data secure?">
                <p>Yes. Data security is a top priority. We use <a href="https://supabase.com" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">Supabase</a>, a trusted backend-as-a-service provider, to securely manage user authentication and data storage. Your troop's data is protected with industry-standard security practices.</p>
            </FaqItem>
        </div>
    </section>
);

const CtaSection = () => (
    <section className="bg-secondary/30">
        <div className="max-w-4xl mx-auto text-center py-16 px-4 sm:py-20 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
                <span className="block">Ready to Modernize Your Troop's Advancement?</span>
            </h2>
            <p className="mt-4 text-lg leading-6 text-text-secondary">
                Join today and bring a new level of efficiency and engagement to your unit.
            </p>
            <Link to="/signup" className="mt-8 inline-block bg-accent text-white font-semibold py-3 px-8 rounded-lg hover:bg-accent-hover transition duration-300 text-lg shadow-[0_0_20px_theme(colors.accent/0.5)]">
                Sign up for free
            </Link>
        </div>
    </section>
);

export const LandingPage: React.FC = () => {
  return (
    <div className="bg-primary text-text-primary">
      <HeroSection />
      <TrustedBySection />
      <HowItWorksSection />
      <FeaturesSection />
      <FaqSection />
      <CtaSection />
    </div>
  );
};
