import React, { useEffect, useState } from 'react';
import {
  Box,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Spinner,
  Text,
  SimpleGrid,
} from '@chakra-ui/react';
import { fetchActivities } from '../services/activity-service';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export default function ActivityDashboard() {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchActivities({ limit: 100 });
        setActivities(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Summarize counts by activity type
  const counts = activities.reduce((acc, a) => {
    const t = a.activity_type;
    acc[t] = (acc[t] || 0) + 1;
    return acc;
  }, {});
  const chartData = Object.keys(counts).map(key => ({ name: key, value: counts[key] }));

  return (
    <Box p={8} mb={8}>
      <Heading mb={4}>Recent Activities</Heading>
      {loading ? (
        <Spinner />
      ) : error ? (
        <Text color="red.500">Error: {error}</Text>
      ) : (
        <>
          <TableContainer mb={6}>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr>
                  <Th>Timestamp</Th>
                  <Th>Type</Th>
                  <Th>Action</Th>
                  <Th>Target</Th>
                  <Th>User</Th>
                  <Th>Description</Th>
                </Tr>
              </Thead>
              <Tbody>
                {activities.map(a => (
                  <Tr key={a.id}>
                    <Td>{new Date(a.timestamp).toLocaleString()}</Td>
                    <Td>{a.activity_type}</Td>
                    <Td>{a.action}</Td>
                    <Td>{a.target_type}/{a.target_name || a.target_id}</Td>
                    <Td>{a.user_id}</Td>
                    <Td>{a.description}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </TableContainer>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
            <Box height={300}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Box>
          </SimpleGrid>
        </>
      )}
    </Box>
  );
}
