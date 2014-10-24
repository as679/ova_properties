__author__ = 'asteer'

import sys
import tarfile
import xml.etree.ElementTree as elementtree

class OVA(object):
    namespace = {'ovf': 'http://schemas.dmtf.org/ovf/envelope/1',
                 'vmw': 'http://www.vmware.com/schema/ovf'}

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        if 'network' not in self.__dict__:
            self.network = None

        if 'ova' in self.__dict__:
            self.ovf = elementtree.parse(self.extractovf(self.ova))
            self.networkProperty = self.parseNetworkSection(self.ovf.find('ovf:NetworkSection', OVA.namespace))
            self.virtualSystemProperties = []
            for tag in ('ovf:VirtualSystemCollection', './/ovf:VirtualSystem'):
                virtualSystems = self.ovf.findall(tag, OVA.namespace)
                if len(virtualSystems) > 0:
                    for virtualSystem in virtualSystems:
                        for property in self.parseVirtualSystem(virtualSystem):
                            self.virtualSystemProperties.append(property)

    def extractovf(self, ova):
        ovf = None
        if tarfile.is_tarfile(ova):
            tar = tarfile.open(ova)
            filenames = tar.getnames()
            if len(filenames) == 0:
                raise Exception('Empty OVA')
            for filename in filenames:
                if filename.endswith('.ovf') and not ovf:
                    ovf = tar.getmember(filename)
                    ovf = tar.extractfile(ovf)
                elif filename.endswith('.ovf') and ovf:
                    raise Exception('Multiple OVF files found')
        return ovf

    def parseNetworkSection(self, networkSection):
        if networkSection is not None:
            for network in networkSection.findall('ovf:Network', OVA.namespace):
                return network.get('{%s}name' % OVA.namespace['ovf'])

    def parseVirtualSystem(self, virtualSystem):
        response = []
        if virtualSystem is not None:
            for productSection in virtualSystem.findall('ovf:ProductSection', OVA.namespace):
                category = productSection.find('ovf:Category', OVA.namespace)
                if category is not None:
                    _class = productSection.get('{%s}class' % OVA.namespace['ovf'])
                    instance = productSection.get('{%s}instance' % OVA.namespace['ovf'])
                    for property in productSection.findall('ovf:Property', OVA.namespace):
                        label = property.find('{%s}Label' % OVA.namespace['ovf'])
                        description = property.find('{%s}Description' % OVA.namespace['ovf'])
                        key = property.get('{%s}key' % OVA.namespace['ovf'])
                        response.append(OVA.OVFProperty(category=category.text,
                                                    label=label.text,
                                                    description=description.text,
                                                    key=key,
                                                    _class=_class,
                                                    instance=instance))
            for vService in virtualSystem.findall('vmw:vServiceDependencySection', OVA.namespace):
                id = vService.get('{%s}id' % OVA.namespace['vmw'])
                response.append(OVA.VServiceDependency(id=id))

        return response

    def cli(self):
        self.network = raw_input('%s: ' % self.networkProperty)
        for property in self.virtualSystemProperties:
            try:
                assert isinstance(property, OVA.OVFProperty)
                property.value = raw_input('%s: ' % property.description)
            except AssertionError as e:
                pass

    def __str__(self):
        str = ""
        str += '"--net:%s=%s"' % (self.networkProperty, self.network) + " "
        for property in self.virtualSystemProperties:
            if property.value is not None and property.value is not "":
                str += property.__str__() + " "
            if isinstance(property, OVA.VServiceDependency):
                str += property.__str__() + " "
        return str


    class OVFProperty(object):
        def __init__(self, **kwargs):
            self.value = None
            for key, value in kwargs.items():
                setattr(self, key, value)

        def __str__(self):
            str = '--prop:'
            for i in (self._class, self.key, self.instance):
                if i is not None:
                    if i is not self.instance and self.instance is not None:
                        str += '%s.' % i
                    else:
                        str += i
            str += '="%s"' % self.value
            return str


    class VServiceDependency(object):
        def __init__(self, **kwargs):
            self.value = None
            for key, value in kwargs.items():
                setattr(self, key, value)

        def __str__(self):
            return '--vService:%s=com.vmware.vim.vsm:extension_vservice' % self.id


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "supply OVA filename"
        sys.exit(1)

    ova = OVA(ova=sys.argv[1])
    ova.cli()

    print ova

