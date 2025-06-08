import React, { useState } from 'react';
import {
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Input,
  Box,
  Flex,
  Avatar,
  Text,
  Badge,
  useColorModeValue,
  Button,
  Stack
} from '@chakra-ui/react';
import { ChevronDownIcon } from '@chakra-ui/icons';

export default function DeviceSelector({ devices = [], selectedDeviceId, onSelect }) {
  const [search, setSearch] = useState('');
  const bgHover = useColorModeValue('gray.100', 'gray.600');
  const filtered = devices.filter(d => d.name.toLowerCase().includes(search.toLowerCase()));
  const selected = devices.find(d => d.hash_id === selectedDeviceId);

  return (
    <Menu isLazy>
      <MenuButton as={Button} rightIcon={<ChevronDownIcon />} variant="outline" minW="200px">
        {selected ? selected.name : 'Select Device'}
      </MenuButton>
      <MenuList p={4} maxH="300px" overflowY="auto" boxShadow="md" borderRadius="md">
        <Input
          placeholder="Search devices..."
          mb={3}
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <Stack spacing={1}>
          {filtered.length > 0 ? filtered.map(d => (
            <MenuItem
              key={d.hash_id}
              _hover={{ bg: bgHover }}
              onClick={() => onSelect(d.hash_id)}
              justifyContent="space-between"
            >
              <Flex align="center">
                <Avatar size="sm" name={d.name} mr={2}/>
                <Text>{d.name}</Text>
              </Flex>
              <Badge colorScheme={d.is_online ? 'green' : 'red'}>
                {d.is_online ? 'Online' : 'Offline'}
              </Badge>
            </MenuItem>
          )) : (
            <Text textAlign="center" color="gray.500">No devices found</Text>
          )}
        </Stack>
      </MenuList>
    </Menu>
  );
}
