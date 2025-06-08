import React from 'react';
import { Flex, Text, HStack, IconButton, useColorMode, useColorModeValue } from '@chakra-ui/react';
import { FiMinus, FiSquare, FiX, FiSun, FiMoon } from 'react-icons/fi';

const ChakraTitleBar = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  return (
    <Flex as="header" position="fixed" top="0" left="0" right="0" h="3rem" bg={bg} borderBottomWidth="1px" borderColor={borderColor} align="center" justify="space-between" px="1rem" zIndex="1000">
      <Text fontSize="lg" fontWeight="bold">IoT Platform</Text>
      <HStack spacing="0.5rem">
        <IconButton
          aria-label="Toggle dark mode"
          icon={colorMode === 'light' ? <FiMoon /> : <FiSun />}
          onClick={toggleColorMode}
          size="sm"
          variant="ghost"
        />
        <IconButton
          aria-label="Minimize"
          icon={<FiMinus />}
          onClick={() => window.electronAPI.minimize()}
          size="sm"
          variant="ghost"
        />
        <IconButton
          aria-label="Maximize"
          icon={<FiSquare />}
          onClick={() => window.electronAPI.maximize()}
          size="sm"
          variant="ghost"
        />
        <IconButton
          aria-label="Close"
          icon={<FiX />}
          onClick={() => window.electronAPI.close()}
          size="sm"
          variant="ghost"
          _hover={{ bg: 'red.500', color: 'white' }}
        />
      </HStack>
    </Flex>
  );
};

export default ChakraTitleBar;
