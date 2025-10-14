import React, { createContext, useState, ReactNode, useContext } from 'react';
import { LoginModal } from '@/components/auth/LoginModal';
import { RegisterModal } from '@/components/auth/RegisterModal';

type ModalType = 'login' | 'register' | null;

interface ModalContextType {
  openModal: (type: ModalType) => void;
  closeModal: () => void;
}

const ModalContext = createContext<ModalContextType | undefined>(undefined);

export const ModalProvider = ({ children }: { children: ReactNode }) => {
  const [modal, setModal] = useState<ModalType>(null);

  const openModal = (type: ModalType) => setModal(type);
  const closeModal = () => setModal(null);

  const handleSwitchToRegister = () => {
    setModal('register');
  };

  const handleSwitchToLogin = () => {
    setModal('login');
  };

  return (
    <ModalContext.Provider value={{ openModal, closeModal }}>
      {children}
      <LoginModal 
        isOpen={modal === 'login'} 
        onClose={closeModal} 
        onSwitchToRegister={handleSwitchToRegister} 
      />
      <RegisterModal 
        isOpen={modal === 'register'} 
        onClose={closeModal} 
        onSwitchToLogin={handleSwitchToLogin} 
      />
    </ModalContext.Provider>
  );
};

export const useModal = () => {
  const context = useContext(ModalContext);
  if (context === undefined) {
    throw new Error('useModal must be used within a ModalProvider');
  }
  return context;
};
