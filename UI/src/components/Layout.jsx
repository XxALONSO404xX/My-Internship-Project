import React, { useState } from 'react';
import {
  Box,
  Drawer,
  DrawerContent,
  useDisclosure,
  IconButton,
  Flex
} from '@chakra-ui/react';
import { useColorModeValue } from '@chakra-ui/react';
import { FiMenu } from 'react-icons/fi';
import Sidebar from './Sidebar';
import { Outlet } from 'react-router-dom';

export default function Layout() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [isExpanded, setIsExpanded] = useState(true);
  const toggleExpand = () => setIsExpanded(prev => !prev);
  const mobileBg = useColorModeValue('white', 'gray.800');
  const mobileBorder = useColorModeValue('gray.200', 'gray.700');
  const mobileText = useColorModeValue('gray.800', 'white');
  return (
    <Box minH="100vh">
      {/* Desktop sidebar */}
      <Sidebar 
        isOpen={isOpen} 
        onClose={onClose} 
        display={{ base: 'none', md: 'flex' }} 
        isExpanded={isExpanded} 
        onToggle={toggleExpand} 
      />
      {/* Mobile drawer */}
      <Drawer
        autoFocus={false}
        isOpen={isOpen}
        placement="left"
        returnFocusOnClose={false}
        onClose={onClose}
        size="full"
      >
        <DrawerContent>
          <Sidebar 
            isOpen={isOpen} 
            onClose={onClose} 
            display={{ base: 'flex', md: 'none' }} 
            isExpanded={isExpanded} 
            onToggle={toggleExpand} 
          />
        </DrawerContent>
      </Drawer>
      {/* Mobile menu button */}
      <Flex
        display={{ base: 'flex', md: 'none' }}
        p={2}
        bg={mobileBg}
        borderBottomWidth="1px"
        borderBottomColor={mobileBorder}
        align="center"
        justify="space-between"
      >
        <IconButton
          variant="outline"
          onClick={onOpen}
          aria-label="Open menu"
          icon={<FiMenu />}
        />
        <Box fontSize="lg" fontWeight="bold" color={mobileText}>
          IoT Dashboard
        </Box>
      </Flex>
      {/* Main content area */}
      <Box ml={{ base: 0, md: isExpanded ? '280px' : '80px' }} p="4">
        <Outlet />
      </Box>
    </Box>
  );
}
