import React, { createContext, useContext, useEffect, useState } from "react";
import {
  type User,
  onAuthStateChanged,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  updateProfile,
} from "firebase/auth";
import { logEvent } from "firebase/analytics";
import { auth, googleProvider, analytics } from "./firebase";
import { API_BASE } from "../services/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, pass: string) => Promise<void>;
  signUpWithEmail: (email: string, pass: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  getIdToken: () => Promise<string | null>;
  isAuthModalOpen: boolean;
  openAuthModal: () => void;
  closeAuthModal: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signInWithGoogle: async () => {},
  signInWithEmail: async () => {},
  signUpWithEmail: async () => {},
  logout: async () => {},
  getIdToken: async () => null,
  isAuthModalOpen: false,
  openAuthModal: () => {},
  closeAuthModal: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Sync login with backend database audit log
  const recordBackendLogin = async (firebaseUser: User) => {
    try {
      const token = await firebaseUser.getIdToken();
      await fetch(`${API_BASE}/auth/record-login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          uid: firebaseUser.uid,
          email: firebaseUser.email,
          name: firebaseUser.displayName,
          photo_url: firebaseUser.photoURL,
        }),
      });
    } catch (e) {
      // Non-blocking background log
      console.warn("Could not log login to backend audit store:", e);
    }
  };

  useEffect(() => {
    if (!auth) {
      setLoading(false);
      return;
    }

    try {
      const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
        setUser(currentUser);
        setLoading(false);
        if (currentUser) {
          // Record analytics event
          if (analytics) {
            try {
              logEvent(analytics, "login", { method: currentUser.providerData[0]?.providerId || "firebase" });
            } catch {}
          }
          // Record in backend audit logs
          recordBackendLogin(currentUser);
        }
      });

      return () => unsubscribe();
    } catch (err) {
      console.warn("Auth state listener initialization failed:", err);
      setLoading(false);
    }
  }, []);

  const signInWithGoogle = async () => {
    if (!auth || !googleProvider) throw new Error("Firebase Auth is not ready.");
    const res = await signInWithPopup(auth, googleProvider);
    if (res.user) {
      await recordBackendLogin(res.user);
    }
  };

  const signInWithEmail = async (email: string, pass: string) => {
    if (!auth) throw new Error("Firebase Auth is not ready.");
    const res = await signInWithEmailAndPassword(auth, email, pass);
    if (res.user) {
      await recordBackendLogin(res.user);
    }
  };

  const signUpWithEmail = async (email: string, pass: string, name?: string) => {
    if (!auth) throw new Error("Firebase Auth is not ready.");
    const res = await createUserWithEmailAndPassword(auth, email, pass);
    if (res.user && name) {
      await updateProfile(res.user, { displayName: name });
    }
    if (res.user) {
      await recordBackendLogin(res.user);
    }
  };

  const logout = async () => {
    if (auth) {
      await signOut(auth);
    }
  };

  const getIdToken = async () => {
    if (!auth || !auth.currentUser) return null;
    return await auth.currentUser.getIdToken();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signInWithGoogle,
        signInWithEmail,
        signUpWithEmail,
        logout,
        getIdToken,
        isAuthModalOpen,
        openAuthModal: () => setIsAuthModalOpen(true),
        closeAuthModal: () => setIsAuthModalOpen(false),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

