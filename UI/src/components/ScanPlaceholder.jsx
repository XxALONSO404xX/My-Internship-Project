import React from 'react';
import { Box, Text, Heading, useColorModeValue } from '@chakra-ui/react';
import { BsRadar } from 'react-icons/bs';
import { keyframes } from '@emotion/react';

// keyframes for rotating sweep
const rotate = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
`;

export default function ScanPlaceholder({ variant }) {
  const ringColor = useColorModeValue('primary.200', 'primary.600');
  const sweepColor = useColorModeValue('rgba(0, 123, 255, 0.35)', 'rgba(0, 123, 255, 0.25)');

  return (
    <Box display="flex" flexDir="column" alignItems="center" justifyContent="center" py={10}>
      {/* Radar container */}
      <Box position="relative" w="220px" h="220px" mb={6}>
        {/* static rings */}
        {[1, 2, 3].map((r) => (
          <Box
            key={r}
            position="absolute"
            inset="0"
            m="auto"
            borderRadius="full"
            borderWidth="1px"
            borderColor={ringColor}
            boxSize={`${r * 70}px`}
            transform={`translate(-50%, -50%) scale(${r / 3})`}
            top="50%"
            left="50%"
          />
        ))}
        {/* rotating sweep */}
        <Box
          position="absolute"
          top="0"
          left="0"
          w="full"
          h="full"
          borderRadius="full"
          overflow="hidden"
          _before={{
            content: '""',
            position: 'absolute',
            inset: 0,
            bgGradient: `conic-gradient(${sweepColor} 0deg, transparent 120deg)`,
            animation: `${rotate} 3s linear infinite`,
          }}
        />
        {/* center icon */}
        <Box position="absolute" top="50%" left="50%" transform="translate(-50%, -50%)" color={ringColor}>
          <BsRadar size={32} />
        </Box>
      </Box>
      {variant === 'no-device' ? (
        <>
          <Heading size="md" mb={2}>Select a Device</Heading>
          <Text textAlign="center" maxW="360px" color={useColorModeValue('gray.600','gray.400')}>
            Choose a device from the dropdown above to enable security features and run vulnerability scans.
          </Text>
        </>
      ) : (
        <>
          <Heading size="md" mb={2}>Ready to Scan</Heading>
          <Text textAlign="center" maxW="360px" color={useColorModeValue('gray.600','gray.400')}>
            Initiate a vulnerability scan to detect and visualise any security issues for the selected device.
          </Text>
        </>
      )}
    </Box>
  );
}
