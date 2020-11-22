from disk import Disk

def diskPartitions():
	a,b,c,d,e,f,g = dsc.getDiskPartitions()
	print("Part Device: {}\nUsage Total: {}\nUsage Used: {}\nUsage Free: {}" \
			"\nUsage Percent: {}\nPart Type: {}\nPart Mountpoint: {}".format(a,b,c,d,e,f,g))

def diskUsage():
	a,b,c,d = dsc.getDiskUsage()
	print("Total: %s Used: %s Free: %s Percent: %s" % (a,b,c,d))


def diskIoCounters():
	a,b,c,d,e,f = dsc.getDiskIoCounters()
	print("Read Count: %s\nWrite Count: %s\nRead Bytes: %s\nWrite Bytes: %s\nRead Times: %s ms\nWrite Time: %s ms"
		% (a,b,c,d,e,f))


if __name__ == "__main__":
	dsc = Disk()
	diskPartitions()
	diskUsage()
	diskIoCounters()