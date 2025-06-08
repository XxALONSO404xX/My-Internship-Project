import React from 'react';
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
  const mobileBg = useColorModeValue('white', 'gray.800');
  const mobileBorder = useColorModeValue('gray.200', 'gray.700');
  const mobileText = useColorModeValue('gray.800', 'white');
  return (
    <Box minH="100vh">
      {/* Desktop sidebar */}
      <Sidebar onClose={onClose} display={{ base: 'none', md: 'block' }} />
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
          <Sidebar onClose={onClose} />
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
      <Box ml={{ base: 0, md: 60 }} p="4">
        <Outlet />
      </Box>
    </Box>
  );
}
