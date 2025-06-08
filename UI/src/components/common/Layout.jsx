import React, { useContext } from 'react';
import { Flex, Box, useColorModeValue, useColorMode, Fade } from '@chakra-ui/react';
import { AuthContext } from '../../contexts/AuthContext';
import ChakraTitleBar from './ChakraTitleBar';
import ChakraSidebar from './ChakraSidebar';

/**
 * Layout component wrapping authenticated views
 */
const Layout = ({ children }) => {
  const bg = useColorModeValue('gray.50', 'gray.900');
  const { user, logout } = useContext(AuthContext);
  const [activeTab, setActiveTab] = React.useState('home');
  const { colorMode } = useColorMode();

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    window.location.hash = `#${tabId}`;
  };

  return (
    <Flex h="100vh" bg={bg}>
      <ChakraTitleBar />
      <ChakraSidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onLogout={logout}
      />
      <Fade in key={colorMode} initialScale={0.98}>
        <Box flex="1" pt="3rem" p={8} overflow="auto">
          {children}
        </Box>
      </Fade>
    </Flex>
  );
};

export default Layout;
