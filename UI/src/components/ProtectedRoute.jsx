import React, { useContext } from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { Spinner, Center } from '@chakra-ui/react';
import { AuthContext } from '../contexts/AuthContext';
import Layout from './Layout';

export default function ProtectedRoute() {
  const { loading, isAuthenticated } = useContext(AuthContext);
  const location = useLocation();

  if (loading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // Authenticated: render layout with nested routes
  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}
